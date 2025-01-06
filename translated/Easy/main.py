import json
from easynmt import EasyNMT
from tqdm import tqdm

# 번역기 초기화
translator = EasyNMT('opus-mt', device='cuda')  # 'cuda'를 지정하여 GPU 사용

def translate_json_easynmt(input_file, output_file):
    """
    기존 JSON 파일을 읽어 필요한 필드를 번역한 후, 번역된 필드를 추가하여 새로운 JSON 파일로 저장합니다.
    
    :param input_file: 번역할 원본 JSON 파일 경로
    :param output_file: 번역된 내용을 저장할 새로운 JSON 파일 경로
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"번역을 시작합니다: {input_file}")
    
    for document in tqdm(data.get("documents", []), desc="문서 번역 중"):
        # 문서 제목 번역 (임베딩용)
        if document.get("document_title"):
            document["document_title_en"] = translator.translate(document["document_title"], source_lang='ko', target_lang='en')
        
        # 조문 순회
        for article in document.get("main_body", []):
            # 조 제목 번역 (임베딩용)
            if article.get("article_title"):
                article["article_title_en"] = translator.translate(article["article_title"], source_lang='ko', target_lang='en')
            
            # 조 본문 번역
            if article.get("article_text"):
                article["article_text_en"] = translator.translate(article["article_text"], source_lang='ko', target_lang='en')
            
            # 항(paragraph) 순회
            for paragraph in article.get("paragraphs", []):
                if paragraph.get("paragraph_text"):
                    paragraph["paragraph_text_en"] = translator.translate(paragraph["paragraph_text"], source_lang='ko', target_lang='en')
                
                # 항 내 아이템 순회
                for item in paragraph.get("items", []):
                    if item.get("item_text"):
                        item["item_text_en"] = translator.translate(item["item_text"], source_lang='ko', target_lang='en')
                    
                    # 하위 아이템(subitems) 순회
                    for subitem in item.get("subitems", []):
                        if subitem.get("subitem_text"):
                            subitem["subitem_text_en"] = translator.translate(subitem["subitem_text"], source_lang='ko', target_lang='en')
                        
                        # 더 깊은 수준(subsubitems)이 있다면 추가로 번역 가능
                        for subsubitem in subitem.get("subsubitems", []):
                            if subsubitem.get("subsubitem_text"):
                                subsubitem["subsubitem_text_en"] = translator.translate(subsubitem["subsubitem_text"], source_lang='ko', target_lang='en')
    
    # 번역된 JSON 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"번역이 완료되었습니다. 저장된 파일: {output_file}")

# 번역할 원본 JSON 파일명과 저장할 번역된 JSON 파일명을 지정합니다.
input_json = '/content/sample_data/output.json'        # 업로드한 JSON 파일명으로 변경하세요.
output_json = '/content/sample_data/translated_easynmt.json'    # 원하는 출력 파일명으로 변경하세요.

translate_json_easynmt(input_json, output_json)
