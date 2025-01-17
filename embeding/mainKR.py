import os
import json
import numpy as np
import torch

from transformers import AutoTokenizer, AutoModel
from tqdm import tqdm

def mean_pooling(model_output, attention_mask):
    """
    Perform mean pooling on the model output to get a single vector.
    """
    token_embeddings = model_output.last_hidden_state  # (batch_size, seq_len, hidden_size)
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    
    # Sum the embeddings for all tokens
    sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, dim=1)
    
    # Count the number of tokens (excluding padded ones)
    sum_mask = torch.clamp(input_mask_expanded.sum(dim=1), min=1e-9)
    
    # Compute the mean
    return sum_embeddings / sum_mask

def embed_text(text, tokenizer, model, device='cpu'):
    """
    Given a single string (text), return its embedding as a NumPy array.
    """
    inputs = tokenizer(
        text, 
        return_tensors='pt', 
        padding=True, 
        truncation=True, 
        max_length=512
    ).to(device)

    with torch.no_grad():
        model_output = model(**inputs)
    
    # Mean pooling
    sentence_embeddings = mean_pooling(model_output, inputs['attention_mask'])
    # (Optional) normalize
    sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)

    return sentence_embeddings.cpu().numpy().squeeze()

def load_embeddings(embeddings_path, chunk_ids_path):
    """
    저장된 임베딩과 청크 ID를 로드하여 반환합니다.
    """
    print(f"임베딩을 '{embeddings_path}'에서 로드 중...")
    embeddings = np.load(embeddings_path)

    print(f"청크 ID를 '{chunk_ids_path}'에서 로드 중...")
    with open(chunk_ids_path, 'r', encoding='utf-8') as f:
        chunk_ids = json.load(f)

    if len(chunk_ids) != len(embeddings):
        raise ValueError("청크 ID의 수와 임베딩의 수가 일치하지 않습니다.")

    return chunk_ids, embeddings

def load_metadata(json_file):
    """
    JSON 파일에서 청크 ID와 메타데이터를 로드하여 매핑합니다.
    """
    print(f"메타데이터를 '{json_file}'에서 로드 중...")
    metadata_map = {}
    with open(json_file, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            chunks = data.get('chunks', [])
            for chunk in chunks:
                chunk_id = chunk.get('chunk_id', '').strip()
                metadata_text = chunk.get('metadata_text', '').strip()
                if chunk_id and metadata_text:
                    # 동일한 chunk_id에 대한 첫 번째 메타데이터만 저장
                    if chunk_id not in metadata_map:
                        metadata_map[chunk_id] = metadata_text
        except json.JSONDecodeError as e:
            print(f"파일 '{json_file}'을(를) 읽는 중 오류 발생: {e}")
    return metadata_map

def calculate_similarity(query_embedding, chunk_embedding_map, top_k=5):
    """
    질의와 가장 유사한 청크를 검색합니다.
    """
    embeddings = np.array([v['embedding'] for v in chunk_embedding_map.values()])
    chunk_ids = list(chunk_embedding_map.keys())
    
    # 코사인 유사도 계산
    embeddings_norm = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
    query_norm = query_embedding / np.linalg.norm(query_embedding)
    cosine_scores = np.dot(embeddings_norm, query_norm)
    
    # 상위 유사도 청크 추출
    top_k_indices = np.argsort(-cosine_scores)[:top_k]
    top_chunks = [
        (chunk_ids[idx], float(cosine_scores[idx]), chunk_embedding_map[chunk_ids[idx]]['metadata_text'])
        for idx in top_k_indices
    ]
    return top_chunks

def main():
    # **1. 설정**
    chunk_directory = 'chunk_json_files'
    output_directory = 'embeddings_output'
    device = 'cuda'

    # **2. KoSimCSE-roberta 모델 로드**
    tokenizer = AutoTokenizer.from_pretrained("BM-K/KoSimCSE-roberta")
    model = AutoModel.from_pretrained("BM-K/KoSimCSE-roberta").to(device)

    # **3. 원본 JSON 파일 경로 설정**
    original_json_file = os.path.join(chunk_directory, 'chunks_output.json')  # 실제 JSON 파일명으로 변경하세요.

    # **4. 임베딩과 chunk_id 로드**
    loaded_chunk_ids, loaded_embeddings = load_embeddings(
        os.path.join(output_directory, 'chunks_output_embeddings.npy'),
        os.path.join(output_directory, 'chunks_output_ids.json')
    )

    # **5. 메타데이터 로드**
    metadata_map = load_metadata(original_json_file)

    # **6. 청크 ID와 임베딩 및 메타데이터 매핑 생성**
    chunk_embedding_map = {}
    for cid, emb in zip(loaded_chunk_ids, loaded_embeddings):
        metadata = metadata_map.get(cid, "메타데이터가 없습니다.")
        chunk_embedding_map[cid] = {
            'embedding': emb,
            'metadata_text': metadata
        }

    # **7. 질의 입력 및 처리 루프**
    print("\n질의를 입력하세요. 종료하려면 '종료', 'exit', 'quit' 중 하나를 입력하세요.\n")
    while True:
        korean_query = input("질의 (한국어): ").strip()
        if korean_query.lower() in ['종료', 'exit', 'quit']:
            print("프로그램을 종료합니다.")
            break
        
        if not korean_query:
            print("빈 입력입니다. 다시 시도해주세요.\n")
            continue
        
        # 한국어 문장을 그대로 임베딩
        print("질의를 한국어 임베딩으로 변환 중...")
        query_embedding = embed_text(korean_query, tokenizer, model, device=device)

        # 유사도 검색
        print("유사도 계산 중...")
        top_chunks = calculate_similarity(query_embedding, chunk_embedding_map, top_k=5)
        
        # 결과 출력
        print("\n상위 5개의 유사한 청크:")
        for idx, (chunk_id, score, metadata) in enumerate(top_chunks, start=1):
            print(f"{idx}. 청크 ID: {chunk_id}, 유사도 점수: {score:.4f}, 메타데이터: {metadata}")
        print("\n-----------------------------\n")

if __name__ == "__main__":
    main()
