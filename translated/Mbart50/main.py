import json
from tqdm.auto import tqdm  # Use tqdm.auto for better Jupyter/Colab support

import torch
from transformers import MBartForConditionalGeneration, MBart50TokenizerFast

# -------------------------------------------------------------------------
# 1. Load MBart50 Model and Tokenizer
# -------------------------------------------------------------------------
model_name = "facebook/mbart-large-50-many-to-many-mmt"

tokenizer = MBart50TokenizerFast.from_pretrained(model_name)
model = MBartForConditionalGeneration.from_pretrained(model_name).to("cuda")  # Move model to GPU


# -------------------------------------------------------------------------
# 2. Count all translatable fields in the JSON
# -------------------------------------------------------------------------
def count_translation_units(data):
    """
    전체 JSON에서 번역해야 할 텍스트 필드의 개수를 세어 반환합니다.
    """
    total_count = 0

    for document in data.get("documents", []):
        # 문서 제목
        if document.get("document_title"):
            total_count += 1

        for article in document.get("main_body", []):
            # 조 제목, 조 본문
            if article.get("article_title"):
                total_count += 1
            if article.get("article_text"):
                total_count += 1

            # 항(paragraph) 내부
            for paragraph in article.get("paragraphs", []):
                if paragraph.get("paragraph_text"):
                    total_count += 1

                # 항 내 아이템
                for item in paragraph.get("items", []):
                    if item.get("item_text"):
                        total_count += 1

                    # 하위 아이템
                    for subitem in item.get("subitems", []):
                        if subitem.get("subitem_text"):
                            total_count += 1

                        # 더 깊은 수준(subsubitems)
                        for subsubitem in subitem.get("subsubitems", []):
                            if subsubitem.get("subsubitem_text"):
                                total_count += 1

    return total_count


# -------------------------------------------------------------------------
# 3. Define the translation function using MBart50
# -------------------------------------------------------------------------
def translate_text(text, src_language="ko_KR", tgt_language="en_XX"):
    """
    MBart50를 이용하여 텍스트를 번역합니다.

    :param text: 번역할 텍스트 (string)
    :param src_language: 소스 언어 코드 (예: 'ko_KR')
    :param tgt_language: 타겟 언어 코드 (예: 'en_XX')
    :return: 번역된 텍스트 (string)
    """
    try:
        if not text:
            return ""

        # 1) 소스 언어 설정
        tokenizer.src_lang = src_language

        # 2) 텍스트를 토크나이즈
        inputs = tokenizer(text, return_tensors="pt", max_length=512, truncation=True).to("cuda")

        # 3) 번역을 생성
        generated_tokens = model.generate(
            **inputs,
            forced_bos_token_id=tokenizer.lang_code_to_id[tgt_language],
            max_length=512,
            num_beams=4
        )

        # 4) 디코딩
        translation = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
        return translation

    except Exception as e:
        print(f"번역 중 오류 발생: {e}")
        return ""


# -------------------------------------------------------------------------
# 4. Define the JSON translation logic with a single, detailed progress bar
# -------------------------------------------------------------------------
def translate_json(input_file, output_file):
    """
    기존 JSON 파일을 읽어 지정된 필드를 번역한 후,
    번역된 필드를 추가하여 새로운 JSON 파일로 저장합니다.
    """
    # JSON 파일 읽기
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 번역해야 하는 모든 텍스트 필드 수 계산
    total_units = count_translation_units(data)
    pbar = tqdm(total=total_units, desc="전체 번역 작업 진행", unit="fields")

    # 번역 시작
    print(f"번역을 시작합니다: {input_file}")

    for document in data.get("documents", []):
        # 문서 제목 번역
        if document.get("document_title"):
            document["document_title_en"] = translate_text(document["document_title"])
            pbar.update(1)

        # 조문 순회
        for article in document.get("main_body", []):
            # 조 제목 번역
            if article.get("article_title"):
                article["article_title_en"] = translate_text(article["article_title"])
                pbar.update(1)

            # 조 본문 번역
            if article.get("article_text"):
                article["article_text_en"] = translate_text(article["article_text"])
                pbar.update(1)

            # 항(paragraph) 순회
            for paragraph in article.get("paragraphs", []):
                if paragraph.get("paragraph_text"):
                    paragraph["paragraph_text_en"] = translate_text(paragraph["paragraph_text"])
                    pbar.update(1)

                # 항 내 아이템 순회
                for item in paragraph.get("items", []):
                    if item.get("item_text"):
                        item["item_text_en"] = translate_text(item["item_text"])
                        pbar.update(1)

                    # 하위 아이템(subitems) 순회
                    for subitem in item.get("subitems", []):
                        if subitem.get("subitem_text"):
                            subitem["subitem_text_en"] = translate_text(subitem["subitem_text"])
                            pbar.update(1)

                        # 더 깊은 수준(subsubitems)
                        for subsubitem in subitem.get("subsubitems", []):
                            if subsubitem.get("subsubitem_text"):
                                subsubitem["subsubitem_text_en"] = translate_text(subsubitem["subsubitem_text"])
                                pbar.update(1)

    pbar.close()  # 모든 번역 작업이 끝나면 progress bar 종료

    # 번역된 JSON 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"번역이 완료되었습니다. 저장된 파일: {output_file}")


# -------------------------------------------------------------------------
# 5. Run the translation
# -------------------------------------------------------------------------
input_json = '/content/drive/MyDrive/Notebook/output.json'         # 업로드한 JSON 파일
output_json = '/content/drive/MyDrive/Notebook/translatedMbart50.json'    # 번역된 JSON 파일

translate_json(input_json, output_json)
