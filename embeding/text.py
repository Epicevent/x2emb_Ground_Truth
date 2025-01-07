import os
import json
import numpy as np
import torch

from sentence_transformers import SentenceTransformer
from googletrans import Translator
from tqdm import tqdm
def load_embeddings(embeddings_path, chunk_ids_path):
    """
    저장된 임베딩과 청크 ID를 로드하여 반환합니다.

    Args:
        embeddings_path (str): 임베딩이 저장된 NumPy 파일 경로.
        chunk_ids_path (str): 청크 ID가 저장된 JSON 파일 경로.

    Returns:
        tuple: (청크 ID 리스트, 임베딩 NumPy 배열)
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

    Args:
        json_file (str): 원본 JSON 파일의 경로.

    Returns:
        dict: 청크 ID를 키로 하고, 메타데이터를 값으로 하는 딕셔너리.
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
def translate_korean_to_english(korean_text, translator):
    """한국어 질의를 영어로 번역합니다."""
    if not korean_text.strip():
        return ""
    return translator.translate(korean_text, src='ko', dest='en').text

def calculate_similarity(query_embedding, chunk_embedding_map, top_k=5):
    """질의와 가장 유사한 청크를 검색합니다."""
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
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    # **2. 모델 초기화**
    embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device=device)
    translator = Translator()
    # **3. 원본 JSON 파일 경로 설정**
    # 임베딩과 chunk_ids가 생성된 원본 JSON 파일의 경로를 지정하세요.
    # 예를 들어, 'chunks_Easy.json'
    original_json_file = os.path.join(chunk_directory, 'chunks_Easy.json')  # 실제 JSON 파일명으로 변경하세요.

    # **4. 임베딩과 chunk_id 로드**
    loaded_chunk_ids, loaded_embeddings = load_embeddings(
    os.path.join(output_directory, 'chunks_Easy_embeddings.npy'),
    os.path.join(output_directory, 'chunks_Easy_chunk_ids.json')
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

    # **4. 질의 입력 및 처리 루프**
    print("\n질의를 입력하세요. 종료하려면 '종료', 'exit', 'quit' 중 하나를 입력하세요.\n")
    while True:
        korean_query = input("질의 (한국어): ").strip()
        if korean_query.lower() in ['종료', 'exit', 'quit']:
            print("프로그램을 종료합니다.")
            break
        
        if not korean_query:
            print("빈 입력입니다. 다시 시도해주세요.\n")
            continue
        
        # 번역
        print("질의를 영어로 번역 중...")
        english_query = translate_korean_to_english(korean_query, translator)
        print(f"번역된 질의: {english_query}")
        
        # 유사도 검색
        print("질의 임베딩 생성 및 유사도 계산 중...")
        query_embedding = embedding_model.encode(english_query, convert_to_numpy=True)
        top_chunks = calculate_similarity(query_embedding, chunk_embedding_map, top_k=5)
        
        # 결과 출력
        print("\n상위 5개의 유사한 청크:")
        for idx, (chunk_id, score, metadata) in enumerate(top_chunks, start=1):
            print(f"{idx}. 청크 ID: {chunk_id}, 유사도 점수: {score:.4f}, 메타데이터: {metadata}")
        print("\n-----------------------------\n")

if __name__ == "__main__":
    main()
