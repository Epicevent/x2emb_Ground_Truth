import json
from collections import Counter
import matplotlib.pyplot as plt

# 1. JSON 파일 로드
def load_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON 디코딩 오류: {e}")
        return None

# 2. chunk_id 추출 및 빈도 계산
def count_chunk_ids(data):
    chunk_ids = []
    for query in data.get("queries", []):
        for content in query.get("content", []):
            chunk_id = content.get("chunk_id")
            if chunk_id:
                chunk_ids.append(chunk_id)
    chunk_id_counts = Counter(chunk_ids)
    return chunk_id_counts

# 3. chunk_id 정렬
def sort_chunk_ids(chunk_id_counts):
    def sort_key(chunk_id):
        return list(map(int, chunk_id.split('.')))
    
    sorted_chunk_ids = sorted(chunk_id_counts.keys(), key=sort_key)
    sorted_counts = [chunk_id_counts[chunk_id] for chunk_id in sorted_chunk_ids]
    return sorted_chunk_ids, sorted_counts

# 4. 히스토그램 그리기
def plot_histogram(sorted_chunk_ids, sorted_counts, save_path='histogram.png'):
    plt.figure(figsize=(12, 6))
    plt.bar(sorted_chunk_ids, sorted_counts, color='skyblue')
    plt.xlabel('Chunk ID')
    plt.ylabel('Frequency')
    plt.title('Histogram of Chunk ID Usage')
    plt.xticks(rotation=90)  # x축 레이블 회전
    plt.tight_layout()
    
    # 플롯을 파일로 저장
    plt.savefig(save_path)
    print(f"플롯이 '{save_path}'로 저장되었습니다.")
    
    # 플롯을 화면에 표시
    plt.show()

def main():
    file_path = 'Ground Truth(1.79-1.92.8).json'  # JSON 파일 경로
    data = load_json(file_path)
    if data is None:
        return
    
    chunk_id_counts = count_chunk_ids(data)
    if not chunk_id_counts:
        print("chunk_id가 발견되지 않았습니다.")
        return
    
    sorted_chunk_ids, sorted_counts = sort_chunk_ids(chunk_id_counts)
    plot_histogram(sorted_chunk_ids, sorted_counts)

if __name__ == "__main__":
    main()
