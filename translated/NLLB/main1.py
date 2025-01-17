import json
from tqdm import tqdm
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# 1. Load the NLLB model and tokenizer
#    Example: facebook/nllb-200-distilled-600M
#             or    facebook/nllb-200-distilled-1.3B
model_name = "facebook/nllb-200-distilled-1.3B"
tokenizer = AutoTokenizer.from_pretrained(model_name, src_lang="kor_Hang")
model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to("cuda")

def count_translation_units(data):
    """
    전체 JSON에서 번역해야 할 텍스트 필드의 개수를 세어 반환합니다.
    """
    total_count = 0

    for document in data.get("documents", []):
        # 문서 제목
        if document.get("document_title"):
            total_count += 1

        # main_body(조문) 순회
        for article in document.get("main_body", []):
            # 조 제목
            if article.get("article_title"):
                total_count += 1
            # 조 본문
            if article.get("article_text"):
                total_count += 1

            # 항(paragraph) 순회
            for paragraph in article.get("paragraphs", []):
                if paragraph.get("paragraph_text"):
                    total_count += 1

                # 항 내 아이템 순회
                for item in paragraph.get("items", []):
                    if item.get("item_text"):
                        total_count += 1

                    # 하위 아이템(subitems) 순회
                    for subitem in item.get("subitems", []):
                        if subitem.get("subitem_text"):
                            total_count += 1

                        # 더 하위 수준(subsubitems)
                        for subsubitem in subitem.get("subsubitems", []):
                            if subsubitem.get("subsubitem_text"):
                                total_count += 1

    return total_count


def translate_text(text, src_lang="ko", tgt_lang="en"):
    """
    NLLB 모델을 이용하여 텍스트를 번역합니다. (Korean -> English)
    
    :param text: 번역할 텍스트 (문자열)
    :param src_lang: 소스 언어 코드 (NLLB 형식, ex. 'kor_Hang')
    :param tgt_lang: 타겟 언어 코드 (NLLB 형식, ex. 'eng_Latn')
    :return: 번역된 텍스트 (문자열)
    """
    try:
        if not text:
            return ""

        # NLLB는 src_lang이 꼭 필요합니다.
        tokenizer.src_lang = src_lang
        tokenizer.tgt_lang = tgt_lang

        # 텍스트를 토크나이즈
        inputs = tokenizer(
            text,
            return_tensors="pt",
            max_length=512,
            truncation=True
        ).to("cuda")

        # 번역을 생성 (forced_bos_token_id를 사용하여 타겟 언어 지정)
        generated_tokens = model.generate(
            **inputs,
            max_length=512,
            num_beams=4
        )

        # 번역 결과 디코딩
        translation = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
        return translation

    except Exception as e:
        print(f"번역 중 오류 발생: {e}")
        return ""


def translate_json_nllb(input_file, output_file):
    """
    기존 JSON 파일을 읽어 필요한 필드를 NLLB로 번역한 후,
    번역된 필드를 추가하여 새로운 JSON 파일로 저장합니다.
    
    :param input_file: 번역할 원본 JSON 파일 경로
    :param output_file: 번역된 내용을 저장할 새로운 JSON 파일 경로
    """
    # JSON 파일 읽기
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"번역을 시작합니다: {input_file}")

    # 1) 번역해야 하는 전체 필드 수를 계산
    total_units = count_translation_units(data)

    # 2) tqdm Progress Bar 초기화 (desc를 좀 더 상세히 표현)
    pbar = tqdm(total=total_units, desc="전체 번역 작업 진행", unit="fields")

    # 3) documents 리스트를 순회하면서 필요한 텍스트 필드들을 번역
    for document in data.get("documents", []):
        # 문서 제목
        if document.get("document_title"):
            document["document_title_en"] = translate_text(document["document_title"], "kor_Hang", "eng_Latn")
            pbar.update(1)  # progress bar 업데이트

        # main_body(조문) 순회
        for article in document.get("main_body", []):
            # 조 제목
            if article.get("article_title"):
                article["article_title_en"] = translate_text(article["article_title"], "kor_Hang", "eng_Latn")
                pbar.update(1)

            # 조 본문
            if article.get("article_text"):
                article["article_text_en"] = translate_text(article["article_text"], "kor_Hang", "eng_Latn")
                pbar.update(1)

            # 항(paragraph) 순회
            for paragraph in article.get("paragraphs", []):
                if paragraph.get("paragraph_text"):
                    paragraph["paragraph_text_en"] = translate_text(paragraph["paragraph_text"], "kor_Hang", "eng_Latn")
                    pbar.update(1)

                # 항 내 아이템 순회
                for item in paragraph.get("items", []):
                    if item.get("item_text"):
                        item["item_text_en"] = translate_text(item["item_text"], "kor_Hang", "eng_Latn")
                        pbar.update(1)

                    # 하위 아이템(subitems) 순회
                    for subitem in item.get("subitems", []):
                        if subitem.get("subitem_text"):
                            subitem["subitem_text_en"] = translate_text(subitem["subitem_text"], "kor_Hang", "eng_Latn")
                            pbar.update(1)

                        # 더 하위(subsubitems) 순회
                        for subsubitem in subitem.get("subsubitems", []):
                            if subsubitem.get("subsubitem_text"):
                                subsubitem["subsubitem_text_en"] = translate_text(
                                    subsubitem["subsubitem_text"], 
                                    "kor_Hang", 
                                    "eng_Latn"
                                )
                                pbar.update(1)

    # 4) 모든 번역이 끝나면 progress bar 종료
    pbar.close()

    # 5) 번역된 JSON 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"번역이 완료되었습니다. 저장된 파일: {output_file}")


# 실제 실행 예시 (경로를 자신의 환경에 맞게 변경하세요)
input_json = "../../output1.json"             # 원본 JSON 파일 경로
output_json = "translated_nllb_kor_to_en.json"  # 번역된 JSON 파일 경로

translate_json_nllb(input_json, output_json)
