import os
import json
import re

def generate_chunks(original_data):
    chunks = []
    for doc in original_data['documents']:
        document_title = doc['document_title']
        docid = doc['document_id']
        
        for article in doc['main_body']:
            # 조(Level) 청크 생성
            article_number = article['article_number']  # e.g., "1조"
            article_title = article['article_title']    # e.g., "목적"
            article_metadata = f"「{document_title}」 {article_number} ({article_title})"
            
            # 조의 content: article_text + all paragraphs' paragraph_text and items' item_text
            article_content = article.get('article_text', '').strip()
            
            for paragraph in article.get('paragraphs', []):
                paragraph_text = paragraph.get('paragraph_text', '').strip()
                items_text = ' '.join([item.get('item_text', '').strip() for item in paragraph.get('items', [])])
                article_content += f" {paragraph_text} {items_text}"
            
            # 조 청크 추가
            # chunk_id: strip "조" from article_number (e.g., "1조" -> "1")
            article_num_match = re.match(r"(\d+)", article_number)
            if article_num_match:
                article_num = article_num_match.group(1)
            else:
                article_num = article_number  # fallback
            
            article_chunk_id = f"{docid}.{article_num}"

            chunks.append({
                "chunk_id": article_chunk_id,
                "chunk_type": "article",
                "metadata_text": article_metadata,
                "content": article_content.strip()
            })
            
            # 항(Level) 청크 생성
            for paragraph in article.get('paragraphs', []):
                paragraph_symbol = paragraph['paragraph_symbol']  # e.g., "①"
                paragraph_text = paragraph.get('paragraph_text', '').strip()
                
                # 항 메타데이터 형식: "「문서 제목」 조번호조항번호" e.g., "「방위사업관리규정」 2조1항"
                unicode_num = ord(paragraph_symbol)
                if 9312 <= unicode_num <= 9331:  # "①" ~ "⑫"
                    num = unicode_num - 9311
                    paragraph_num_label = f"{num}항"
                else:
                    # 예상치 못한 심볼 처리 (기본값: "1항")
                    paragraph_num_label = "1항"
                
                paragraph_metadata = f"「{document_title}」 {article_num}조{paragraph_num_label}"
                
                # 항 내용: paragraph_text + all items' item_text
                items_text = ' '.join([item.get('item_text', '').strip() for item in paragraph.get('items', [])])
                paragraph_content = f"{paragraph_text} {items_text}".strip()
               
                # chunk_id: "{조번호}.{항번호}" (e.g., "1.1")
                # Extract integer from paragraph_symbol (e.g., "①" -> "1")
                paragraph_num_match = re.match(r"\d+", paragraph_symbol)
                if paragraph_num_match:
                    paragraph_num = paragraph_num_match.group()
                else:
                    # Convert Unicode symbol "①" -> 1, etc.
                    paragraph_num = str(unicode_num - 9311)
                    if not paragraph_num.isdigit():
                        paragraph_num = "1"  # default
                
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
    input_folder = "inputKR"
    output_folder = "outputKR"

    # Process all documents in the input folder
    process_all_documents(input_folder, output_folder)
