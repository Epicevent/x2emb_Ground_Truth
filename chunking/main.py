import os
import json
import re
def generate_chunks(original_data):
    chunks = []
    for doc in original_data['documents']:
        document_title = doc['document_title']
        docid= doc['document_id']
        for article in doc['main_body']:
            # 조(Level) 청크 생성
            article_number = article['article_number']  # 예: "1조"
            article_title = article['article_title']    # 예: "목적"
            article_metadata = f"「{document_title}」 {article_number} ({article_title})"
            
            # 조의 content: article_text_en + 모든 항의 paragraph_text_en 및 items text_en
            article_content = article.get('article_text_en', '').strip()
            for paragraph in article.get('paragraphs', []):
                paragraph_text_en = paragraph.get('paragraph_text_en', '').strip()
                items_text_en = ' '.join([item.get('item_text_en', '').strip() for item in paragraph.get('items', [])])
                article_content += ' ' + paragraph_text_en + ' ' + items_text_en
            
            # 조 청크 추가
            # chunk_id: 조 번호에서 '조'를 제거 (예: "1조" -> "1")
            article_num_match = re.match(r"(\d+)", article_number)
            if article_num_match:
                article_num = article_num_match.group(1)
            else:
                article_num = article_number  # Fallback
            
            article_chunk_id = f"{docid}.{article_num}"

            chunks.append({
                "chunk_id": article_chunk_id,
                "chunk_type": "article",
                "metadata_text": article_metadata,
                "content": article_content
            })
            
            # 항(Level) 청크 생성
            for paragraph in article.get('paragraphs', []):
                paragraph_symbol = paragraph['paragraph_symbol']  # 예: "①"
                # paragraph_text = paragraph['paragraph_text']      # 항 제목은 제외
                paragraph_text_en = paragraph.get('paragraph_text_en', '').strip()
                
                # 항 메타데이터
                # 형식: "「문서 제목」 조번호조항번호"
                # 예: "「방위사업관리규정」 2조1항"

                # 유니코드 숫자 심볼 변환
                unicode_num = ord(paragraph_symbol)
                if 9312 <= unicode_num <= 9331:  # "①" ~ "⑫"
                    num = unicode_num - 9311
                    paragraph_num = f"{num}항"
                else:
                    # 예상치 못한 심볼 처리 (기본값: "1항")
                    paragraph_num = "1항"
                
                paragraph_metadata = f"「{document_title}」 {article_num}조{paragraph_num}"
                
                # 항 내용: paragraph_text_en + 모든 목의 text_en
                items_text_en = ' '.join([item.get('item_text_en', '').strip() for item in paragraph.get('items', [])])
                paragraph_content = paragraph_text_en + ' ' + items_text_en
               
                # chunk_id: 조번호.항번호 (예: "1.1")
                # 숫자 추출: "①" -> "1"
                paragraph_num_match = re.match(r"\d+", paragraph_symbol)
                if paragraph_num_match:
                    paragraph_num = paragraph_num_match.group()
                else:
                    # 유니코드 숫자 변환
                    # "①"은 유니코드에서 '1'에 해당
                    paragraph_num = str(ord(paragraph_symbol) - 9311)  # '①' is U+2460
                    if not paragraph_num.isdigit():
                        paragraph_num = '1'  # Default
                
                paragraph_chunk_id = f"{docid}.{article_num}.{paragraph_num}"
                
                chunks.append({
                    "chunk_id": paragraph_chunk_id,
                    "chunk_type": "paragraph",
                    "metadata_text": paragraph_metadata,
                    "content": paragraph_content
                })
    
    return {"chunks": chunks}

def process_all_documents(input_folder, output_folder):
    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Iterate through all JSON files in the input folder
    for file_name in os.listdir(input_folder):
        if file_name.endswith('.json'):
            input_file_path = os.path.join(input_folder, file_name)

            # Read the input JSON file
            with open(input_file_path, 'r', encoding='utf-8') as f:
                doc_json = json.load(f)

            # Generate chunks
            chunks = generate_chunks(doc_json)

            # Save chunks to a new JSON file in the output folder
            output_file_name = f"chunks_{file_name}"
            output_file_path = os.path.join(output_folder, output_file_name)
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(chunks, f, indent=4, ensure_ascii=False)

            print(f"Processed and saved: {output_file_name}")

if __name__ == "__main__":
    input_folder = "input"
    output_folder = "output"

    # Process all documents in the input folder
    process_all_documents(input_folder, output_folder)
