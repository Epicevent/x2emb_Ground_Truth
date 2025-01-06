import json
from transformers import MarianMTModel, MarianTokenizer
from tqdm import tqdm
import torch

# 번역기 초기화
translation_model_name = "Helsinki-NLP/opus-mt-ko-en"  # 한국어-영어 번역 모델
tokenizer = MarianTokenizer.from_pretrained(translation_model_name)
model = MarianMTModel.from_pretrained(translation_model_name).to('cuda')  # GPU로 모델 이동

def translate_text_marian(texts):
    """
    주어진 텍스트 목록을 영어로 번역합니다.
    
    :param texts: 번역할 텍스트 목록
    :return: 번역된 텍스트 목록
    """
    translated = []
    batch_size = 16  # 배치 사이즈 조절 가능
    for i in tqdm(range(0, len(texts), batch_size), desc="MarianMT 번역 중"):
        batch = texts[i:i+batch_size]
        inputs = tokenizer(batch, return_tensors="pt", padding=True, truncation=True).to('cuda')
        with torch.no_grad():
            translated_tokens = model.generate(**inputs)
        batch_translated = tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)
        translated.extend(batch_translated)
    return translated

def translate_json_marian(input_file, output_file):
    """
    기존 JSON 파일을 읽어 필요한 필드를 번역한 후, 번역된 필드를 추가하여 새로운 JSON 파일로 저장합니다.
    
    :param input_file: 번역할 원본 JSON 파일 경로
    :param output_file: 번역된 내용을 저장할 새로운 JSON 파일 경로
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"번역을 시작합니다: {input_file}")
    
    # 번역할 텍스트 수집
    document_titles = [doc.get("document_title", "") for doc in data.get("documents", [])]
    article_titles = []
    article_texts = []
    paragraph_texts = []
    item_texts = []
    subitem_texts = []
    subsubitem_texts = []
    
    for doc in data.get("documents", []):
        for article in doc.get("main_body", []):
            if article.get("article_title"):
                article_titles.append(article.get("article_title"))
            if article.get("article_text"):
                article_texts.append(article.get("article_text"))
            for paragraph in article.get("paragraphs", []):
                if paragraph.get("paragraph_text"):
                    paragraph_texts.append(paragraph.get("paragraph_text"))
                for item in paragraph.get("items", []):
                    if item.get("item_text"):
                        item_texts.append(item.get("item_text"))
                    for subitem in item.get("subitems", []):
                        if subitem.get("subitem_text"):
                            subitem_texts.append(subitem.get("subitem_text"))
                        for subsubitem in subitem.get("subsubitems", []):
                            if subsubitem.get("subsubitem_text"):
                                subsubitem_texts.append(subsubitem.get("subsubitem_text"))
    
    # 번역 수행
    translated_document_titles = translate_text_marian(document_titles)
    translated_article_titles = translate_text_marian(article_titles)
    translated_article_texts = translate_text_marian(article_texts)
    translated_paragraph_texts = translate_text_marian(paragraph_texts)
    translated_item_texts = translate_text_marian(item_texts)
    translated_subitem_texts = translate_text_marian(subitem_texts)
    translated_subsubitem_texts = translate_text_marian(subsubitem_texts)
    
    # 번역된 텍스트 할당
    doc_idx = 0
    art_title_idx = 0
    art_text_idx = 0
    para_text_idx = 0
    item_text_idx = 0
    subitem_text_idx = 0
    subsubitem_text_idx = 0
    
    for doc in data.get("documents", []):
        # 문서 제목 번역
        if doc.get("document_title"):
            doc["document_title_en"] = translated_document_titles[doc_idx]
            doc_idx += 1
        # 조문 번역
        for article in doc.get("main_body", []):
            # 조 제목 번역
            if article.get("article_title"):
                article["article_title_en"] = translated_article_titles[art_title_idx]
                art_title_idx += 1
            # 조 본문 번역
            if article.get("article_text"):
                article["article_text_en"] = translated_article_texts[art_text_idx]
                art_text_idx += 1
            # 항(paragraph) 번역
            for paragraph in article.get("paragraphs", []):
                if paragraph.get("paragraph_text"):
                    paragraph["paragraph_text_en"] = translated_paragraph_texts[para_text_idx]
                    para_text_idx += 1
                # 아이템 번역
                for item in paragraph.get("items", []):
                    if item.get("item_text"):
                        item["item_text_en"] = translated_item_texts[item_text_idx]
                        item_text_idx += 1
                    # 하위 아이템 번역
                    for subitem in item.get("subitems", []):
                        if subitem.get("subitem_text"):
                            subitem["subitem_text_en"] = translated_subitem_texts[subitem_text_idx]
                            subitem_text_idx += 1
                        # 더 깊은 수준 번역
                        for subsubitem in subitem.get("subsubitems", []):
                            if subsubitem.get("subsubitem_text"):
                                subsubitem["subsubitem_text_en"] = translated_subsubitem_texts[subsubitem_text_idx]
                                subsubitem_text_idx += 1
    
    # 번역된 JSON 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"번역이 완료되었습니다. 저장된 파일: {output_file}")

# 번역할 원본 JSON 파일명과 저장할 번역된 JSON 파일명을 지정합니다.
input_json = '/content/sample_data/output.json'        # 업로드한 JSON 파일명으로 변경하세요.
output_json = '/content/sample_data/translated_marian.json'    # 원하는 출력 파일명으로 변경하세요.

translate_json_marian(input_json, output_json)
