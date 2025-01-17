import os
import json
import numpy as np
import torch

from transformers import AutoTokenizer, AutoModel
from tqdm import tqdm

def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output.last_hidden_state  # (batch_size, seq_len, hidden_size)
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()

    sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, dim=1)
    sum_mask = torch.clamp(input_mask_expanded.sum(dim=1), min=1e-9)
    return sum_embeddings / sum_mask

def embed_text(text, tokenizer, model, device='cpu'):
    inputs = tokenizer(
        text,
        return_tensors='pt',
        padding=True,
        truncation=True,
        max_length=512
    ).to(device)

    with torch.no_grad():
        model_output = model(**inputs)

    sentence_embeddings = mean_pooling(model_output, inputs['attention_mask'])
    # (Optional) L2 normalize
    sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)

    return sentence_embeddings.cpu().numpy().squeeze()

def load_embeddings(embeddings_path, chunk_ids_path):
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
    원본 JSON에서 chunk_id마다 'metadata_text'와 'content' 모두 로드합니다.
    예시 JSON 구조 (가정):
    {
      "chunks": [
        {
          "chunk_id": "chunk_1",
          "metadata_text": "이곳은 메타데이터 예시입니다.",
          "content": "이곳은 실제 본문(content)에 해당하는 예시입니다."
        },
        ...
      ]
    }
    """
    print(f"메타데이터를 '{json_file}'에서 로드 중...")
    metadata_map = {}
    with open(json_file, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            chunks = data.get('chunks', [])
            for chunk in chunks:
                chunk_id = chunk.get('chunk_id', '').strip()
                if not chunk_id:
                    continue

                # Read both metadata_text and content
                metadata_text = chunk.get('metadata_text', '').strip()
                content = chunk.get('content', '').strip()

                # Store both fields in the dictionary
                metadata_map[chunk_id] = {
                    'metadata_text': metadata_text,
                    'content': content
                }
        except json.JSONDecodeError as e:
            print(f"파일 '{json_file}'을(를) 읽는 중 오류 발생: {e}")
    return metadata_map

def calculate_similarity(query_embedding, chunk_embedding_map, top_k=5):
    """
    질의와 가장 유사한 청크를 검색하고,
    (chunk_id, 유사도 점수) 튜플 리스트를 반환합니다.
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
        (chunk_ids[idx], float(cosine_scores[idx]))
        for idx in top_k_indices
    ]
    return top_chunks

def query_text(korean_query, chunk_embedding_map, tokenizer, model, device='cpu', top_k=5, verbose=True):
    """
    단일 한국어 질의에 대해 top_k 유사 청크를 반환 (및 출력)하는 함수.
    여기서 'metadata_text'와 'content' 둘 다 보여줄 수 있습니다.
    """
    # 1) 한국어 문장을 임베딩
    query_embedding = embed_text(korean_query, tokenizer, model, device=device)

    # 2) 유사도 계산 (returns (chunk_id, score))
    top_chunks = calculate_similarity(query_embedding, chunk_embedding_map, top_k=top_k)

    # 3) 결과를 리턴하고, 옵션으로 출력
    if verbose:
        print(f"\n질의: {korean_query}")
        print(f"상위 {top_k}개의 유사한 청크:")

        for idx, (chunk_id, score) in enumerate(top_chunks, start=1):
            # Retrieve both metadata_text and content
            metadata_text = chunk_embedding_map[chunk_id].get('metadata_text', 'N/A')
            content = chunk_embedding_map[chunk_id].get('content', 'N/A')
            
            print(f"{idx}. 청크 ID: {chunk_id}")
            print(f"   - 유사도 점수: {score:.4f}")
            print(f"   - metadata_text: {metadata_text}")
            print(f"   - content: {content}")
            print()

        print("-----------------------------\n")

    return top_chunks

def main():
    # **1. 설정**
    chunk_directory = 'chunk_json_files_kr'
    output_directory = 'embeddings_output_kr'
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # **2. 모델 로드 (KoSimCSE-roberta)**
    tokenizer = AutoTokenizer.from_pretrained("BM-K/KoSimCSE-roberta")
    model = AutoModel.from_pretrained("BM-K/KoSimCSE-roberta").to(device)

    # **3. JSON 파일 경로 (원본)**
    original_json_file = os.path.join(chunk_directory, 'chunks_output.json')

    # **4. 사전에 저장된 임베딩과 chunk_id 로드**
    loaded_chunk_ids, loaded_embeddings = load_embeddings(
        os.path.join(output_directory, 'chunks_output_embeddings.npy'),
        os.path.join(output_directory, 'chunks_output_ids.json')
    )

    # **5. 메타데이터(여기서는 metadata_text, content) 로드**
    metadata_map = load_metadata(original_json_file)

    # **6. chunk_id -> (embedding, metadata_text, content) 매핑 생성**
    chunk_embedding_map = {}
    for cid, emb in zip(loaded_chunk_ids, loaded_embeddings):
        # Get the dictionary with keys 'metadata_text' and 'content'
        meta_info = metadata_map.get(cid, {})
        metadata_text = meta_info.get('metadata_text', '')
        content = meta_info.get('content', '')

        chunk_embedding_map[cid] = {
            'embedding': emb,
            'metadata_text': metadata_text,
            'content': content
        }

    # **7. 사용자 질의 루프 (또는 단일 호출)**
    print("\n질의를 입력하세요. 종료하려면 '종료', 'exit', 'quit' 중 하나를 입력하세요.\n")
    while True:
        korean_query = input("질의 (한국어): ").strip()
        if korean_query.lower() in ['종료', 'exit', 'quit']:
            print("프로그램을 종료합니다.")
            break
        if not korean_query:
            print("빈 입력입니다. 다시 시도해주세요.\n")
            continue

        # Top-k 유사 청크를 조회
        query_text(korean_query, chunk_embedding_map, tokenizer, model, device=device, top_k=5, verbose=True)

if __name__ == "__main__":
    main()
