import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import torch

def generate_unique_chunk_id(original_chunk_id, occurrence):
    """
    고유한 chunk_id를 생성하기 위해 원래의 chunk_id와 발생 횟수를 결합합니다.

    Args:
        original_chunk_id (str): 원래의 chunk_id.
        occurrence (int): chunk_id의 발생 횟수.

    Returns:
        str: 고유한 chunk_id.
    """
    if occurrence == 1:
        return original_chunk_id
    else:
        return f"{original_chunk_id}_{occurrence-1}"

def process_single_json(json_file, embedding_model):
    """
    단일 JSON 파일을 처리하여 고유한 chunk_id에 대한 임베딩을 생성하고 반환합니다.

    Args:
        json_file (str): 처리할 JSON 파일의 경로.
        embedding_model (SentenceTransformer): 임베딩 생성에 사용할 모델.

    Returns:
        tuple: (고유한 chunk_id 리스트, 임베딩 NumPy 배열)
    """
    chunk_ids = []
    contents = []
    
    with open(json_file, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            chunks = data.get('chunks', [])
            
            # chunk_id 발생 횟수 추적을 위한 딕셔너리
            chunk_id_counts = {}
            
            for chunk in chunks:
                original_chunk_id = chunk.get('chunk_id', '').strip()
                content = chunk.get('content', '').strip()
                
                if original_chunk_id and content:
                    # 현재 chunk_id의 발생 횟수 업데이트
                    if original_chunk_id in chunk_id_counts:
                        chunk_id_counts[original_chunk_id] += 1
                    else:
                        chunk_id_counts[original_chunk_id] = 1
                    
                    occurrence = chunk_id_counts[original_chunk_id]
                    unique_chunk_id = generate_unique_chunk_id(original_chunk_id, occurrence)
                    
                    # 첫 번째 발생만 임베딩을 생성하고 이후는 무시
                    if occurrence == 1:
                        chunk_ids.append(unique_chunk_id)
                        contents.append(content)
        except json.JSONDecodeError as e:
            print(f"파일 '{json_file}'을(를) 읽는 중 오류 발생: {e}")
    
    if not chunk_ids:
        print(f"파일 '{json_file}'에는 유효한 청크가 없습니다.")
        return None, None
    
    # 임베딩 생성
    embeddings = embedding_model.encode(contents, batch_size=32, show_progress_bar=False, convert_to_numpy=True)
    
    return chunk_ids, embeddings

def generate_embeddings_for_all_json(chunk_dir, output_dir):
    """
    지정된 디렉토리 내의 모든 JSON 파일을 처리하여 임베딩을 생성하고 저장합니다.

    Args:
        chunk_dir (str): 청킹된 JSON 파일들이 있는 디렉토리 경로.
        output_dir (str): 생성된 임베딩과 chunk_id를 저장할 디렉토리 경로.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 임베딩 모델 초기화
    print("임베딩 모델 초기화 중...")
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device=device)
    
    # JSON 파일 리스트
    json_files = [file for file in os.listdir(chunk_dir) if file.endswith('.json')]
    
    if not json_files:
        print(f"디렉토리 '{chunk_dir}'에 JSON 파일이 없습니다. 스크립트를 종료합니다.")
        return
    
    print(f"총 {len(json_files)}개의 JSON 파일을 발견했습니다.")
    
    # 각 JSON 파일별로 처리
    for json_file in tqdm(json_files, desc="JSON 파일 처리 중", unit="file"):
        json_path = os.path.join(chunk_dir, json_file)
        print(f"\n처리 중: {json_file}")
        
        chunk_ids, embeddings = process_single_json(json_path, embedding_model)
        
        if chunk_ids and embeddings is not None:
            # 출력 파일명 생성
            base_name = os.path.splitext(json_file)[0]
            embeddings_output_path = os.path.join(output_dir, f"{base_name}_embeddings.npy")
            chunk_ids_output_path = os.path.join(output_dir, f"{base_name}_chunk_ids.json")
            
            # 임베딩 저장
            np.save(embeddings_output_path, embeddings)
            print(f"임베딩을 '{embeddings_output_path}'에 저장했습니다.")
            
            # chunk_id 저장
            with open(chunk_ids_output_path, 'w', encoding='utf-8') as f:
                json.dump(chunk_ids, f, ensure_ascii=False, indent=4)
            print(f"청크 ID를 '{chunk_ids_output_path}'에 저장했습니다.")
        else:
            print(f"파일 '{json_file}'을(를) 처리하는 동안 유효한 청크가 없어 임베딩을 생성하지 않았습니다.")

def load_embeddings(embeddings_path, chunk_ids_path):
    """
    저장된 임베딩과 청크 ID를 로드하여 매핑합니다.

    Args:
        embeddings_path (str): 임베딩이 저장된 NumPy 파일 경로.
        chunk_ids_path (str): 청크 ID가 저장된 JSON 파일 경로.

    Returns:
        dict: 청크 ID를 키로 하고, 임베딩을 값으로 하는 딕셔너리.
    """
    print(f"임베딩을 '{embeddings_path}'에서 로드 중...")
    embeddings = np.load(embeddings_path)
    
    print(f"청크 ID를 '{chunk_ids_path}'에서 로드 중...")
    with open(chunk_ids_path, 'r', encoding='utf-8') as f:
        chunk_ids = json.load(f)
    
    if len(chunk_ids) != len(embeddings):
        raise ValueError("청크 ID의 수와 임베딩의 수가 일치하지 않습니다.")
    
    print("청크 ID와 임베딩을 매핑 중...")
    chunk_embedding_map = {cid: emb for cid, emb in zip(chunk_ids, embeddings)}
    
    return chunk_embedding_map

def example_similarity_search(query, embedding_model, chunk_embedding_map, top_k=5):
    """
    주어진 질의에 대해 유사한 청크를 검색합니다.

    Args:
        query (str): 질의 문자열.
        embedding_model (SentenceTransformer): 임베딩 모델.
        chunk_embedding_map (dict): 청크 ID를 임베딩으로 매핑한 딕셔너리.
        top_k (int): 상위 몇 개의 유사한 청크를 반환할지 설정.

    Returns:
        list: (청크 ID, 유사도 점수) 튜플의 리스트.
    """
    print(f"질의 '{query}'에 대한 임베딩 생성 중...")
    query_embedding = embedding_model.encode(query, convert_to_numpy=True)
    
    print("코사인 유사도 계산 중...")
    embeddings = np.array(list(chunk_embedding_map.values()))
    chunk_ids = list(chunk_embedding_map.keys())
    
    # 임베딩 정규화
    embeddings_norm = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
    query_norm = query_embedding / np.linalg.norm(query_embedding)
    
    # 코사인 유사도 계산
    cosine_scores = np.dot(embeddings_norm, query_norm)
    
    # 상위 top_k 인덱스 추출
    top_k_indices = np.argsort(-cosine_scores)[:top_k]
    
    top_chunks = [(chunk_ids[idx], float(cosine_scores[idx])) for idx in top_k_indices]
    
    return top_chunks

# **실행 예시**
if __name__ == "__main__":
    # **1. 청킹된 JSON 파일들이 있는 디렉토리 경로 설정**
    chunk_directory = 'chunk_json_files'       # 실제 JSON 파일들이 있는 디렉토리로 변경하세요.
    
    # **2. 출력 파일들이 저장될 디렉토리 설정**
    output_directory = 'embeddings_output'     # 임베딩과 chunk_id를 저장할 디렉토리
    
    # **3. 임베딩 생성 및 저장**
    generate_embeddings_for_all_json(chunk_directory, output_directory)
    
    # **4. 예시 유사도 검색 (선택 사항)**
    # 특정 JSON 파일에 대한 임베딩과 chunk_id를 로드하여 유사도 검색을 수행할 수 있습니다.
    """
    # 예시: 'document1.json'의 임베딩과 chunk_id 로드
    loaded_chunk_ids, loaded_embeddings = load_embeddings(
        os.path.join(output_directory, 'document1_embeddings.npy'),
        os.path.join(output_directory, 'document1_chunk_ids.json')
    )
    
    # chunk_embedding_map 생성
    chunk_embedding_map = {cid: emb for cid, emb in zip(loaded_chunk_ids, loaded_embeddings)}
    
    # 임베딩 모델 초기화 (이미 초기화된 경우 생략 가능)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device=device)
    
    # 예시 질의
    example_query = "What are the regulations for defense operations?"
    top_chunks = example_similarity_search(example_query, embedding_model, chunk_embedding_map, top_k=5)
    
    print("\n상위 5개의 유사한 청크:")
    for chunk_id, score in top_chunks:
        print(f"청크 ID: {chunk_id}, 유사도 점수: {score:.4f}")
    """
