import os
import json
from PyPDF2 import PdfReader
import re

# 1) 하드코딩된 열거자 리스트
LEVEL1_ENUMS = [
    "①","②","③","④","⑤","⑥","⑦","⑧","⑨","⑩",
    "⑪","⑫","⑬","⑭","⑮","⑯","⑰","⑱","⑲","⑳",
    "㉑","㉒","㉓","㉔","㉕","㉖","㉗","㉘","㉙","㉚",
    "㉛","㉜","㉝","㉞","㉟"
]

LEVEL3_ENUMS = [
    "가.", "나.", "다.", "라.", "마.", "바.", "사.", "아.", "자.", "차."
]

# 2) 동적으로 정의된 열거자 패턴
LEVEL2_PATTERN = re.compile(r"^\d+\.\s*")    # 예: 1., 2., 3., ..., 35.
LEVEL4_PATTERN = re.compile(r"^\d+\)\s*")    # 예: 1), 2), 3), ..., 35)

# 3) 조(條) 패턴: 공백 허용 및 추가 콘텐츠 캡처
SECTION_PATTERN = re.compile(r"^제\s*(\d+조(?:의\d+)*)\s*\((.*?)\)\s*(.*)$")

def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a PDF file.
    PDF 파일로부터 텍스트를 추출합니다.
    """
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return ""

def clean_unwanted_lines(lines):
    """
    Removes lines that seem to be headers/footers or purely numeric (page numbers).
    '법제처', '국가법령정보센터' 등이 포함된 라인 또는 페이지 번호(숫자만 있는 라인)를 제거합니다.
    
    헤더/푸터로 추정되는 줄을 제거하는 함수입니다.
    """
    cleaned = []
    for line in lines:
        # '법제처' 또는 '국가법령정보센터'가 포함된 라인 제외
        if "법제처" in line or "국가법령정보센터" in line:
            continue
        
        # 순수 숫자로만 구성된 라인 제외 (페이지 번호로 추정)
        if line.strip().isdigit():
            continue
        
        # 기타 불필요한 패턴이 있다면 추가로 필터링 가능
        cleaned.append(line)
    return cleaned
def parse_filename(file_name):
    """
    Parses the filename to extract document metadata.
    파일 이름을 파싱하여 문서 메타데이터를 추출합니다.
    
    형식: 방위사업관리규정(방위사업청훈령)(제864호)(20240711).pdf
    """
    # 파일 확장자 제거
    base_name = os.path.splitext(file_name)[0]
    # 정규표현식으로 파싱
    pattern = re.compile(r"^(.*?)\((.*?)\)\((.*?)\)\((\d{8})\)$")
    match = pattern.match(base_name)
    if match:
        document_title = match.group(1).strip()
        document_type = match.group(2).strip()
        promulgation_number = match.group(3).strip()
        enforcement_date = match.group(4).strip()
        return {
            "document_title": document_title,
            "document_type": document_type,
            "promulgation_number": promulgation_number,
            "enforcement_date": enforcement_date
        }
    else:
        print(f"Filename '{file_name}' does not match the expected pattern.")
        return {
            "document_title": base_name,
            "document_type": "",
            "promulgation_number": "",
            "enforcement_date": ""
        }

def parse_text_to_structure(text, doc_id, title):
    """
    Parses the extracted text into a structured JSON format.
    - Skips unwanted lines (headers/footers).
    - Identifies sections with '제n조(...)' or '제n조의m(...)'.
    - Handles enumerators based on hardcoded (level1, level3) and dynamic (level2, level4) patterns.
    - Accumulates multi-line content under the correct enumerator/section.
    
    추출된 텍스트를 구조화된 JSON 형식으로 파싱합니다.
    """
    
    # 텍스트를 줄 단위로 분할 후, 알려진 헤더/푸터를 제거합니다.
    lines = text.split("\n")
    lines = clean_unwanted_lines(lines)

    # 최종 JSON 구조를 담을 딕셔너리
    document = {
        "document_id": str(doc_id),
        "document_title": title,
        "document_type": "",              # 필요 시 채움 (예: 법률, 대통령령 등)
        "promulgation_number": "",        # 필요 시 채움 (공포번호 등)
        "main_body": []                   # 본문 조문
    }

    current_article = None
    current_paragraph = None
    current_item = None
    current_subitem = None

    for line_number, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue  # 빈 줄 건너뜀

        # 1) 조(條) 인식
        match_section = SECTION_PATTERN.match(line)
        if match_section:
            # 새로운 조가 나오면 기존의 조를 마무리
            if current_article:
                document["main_body"].append(current_article)
            
            article_number = match_section.group(1)      # 예: '6조', '6조의2'
            article_title = match_section.group(2)       # 예: '보안과제'
            additional_content = match_section.group(3).strip()  # 추가 콘텐츠, 있을 경우

            current_article = {
                "article_number": article_number,
                "article_title": article_title,
                "article_text": "",
                "paragraphs": []
            }
            # Reset all lower levels
            current_paragraph = None
            current_item = None
            current_subitem = None

            # 추가 콘텐츠가 있을 경우
            if additional_content:
                # 추가 콘텐츠가 항의 시작 기호로 시작하는지 확인
                is_paragraph = False
                for symbol in LEVEL1_ENUMS:
                    if additional_content.startswith(symbol):
                        is_paragraph = True
                        content = additional_content[len(symbol):].strip()
                        current_paragraph = {
                            "paragraph_symbol": symbol,
                            "paragraph_text": content,
                            "items": []
                        }
                        current_article["paragraphs"].append(current_paragraph)
                        break
                if not is_paragraph:
                    # 항이 없는 경우, article_text에 추가
                    current_article["article_text"] = additional_content
            continue

        # 2) 레벨 1 열거자 인식 (하드코딩된 리스트 사용)
        if any(line.startswith(symbol) for symbol in LEVEL1_ENUMS):
            for symbol in LEVEL1_ENUMS:
                if line.startswith(symbol):
                    content = line[len(symbol):].strip()
                    # 항(paragraph) 추가
                    current_paragraph = {
                        "paragraph_symbol": symbol,
                        "paragraph_text": content,
                        "items": []
                    }
                    current_article["paragraphs"].append(current_paragraph)
                    # Reset lower levels
                    current_item = None
                    current_subitem = None
                    break
            continue

        # 3) 레벨 2 열거자 인식 (동적 패턴 사용)
        match_level2 = LEVEL2_PATTERN.match(line)
        if match_level2 and current_paragraph:
            enumerator = match_level2.group(0).strip()
            content = line[match_level2.end():].strip()
            # 호(item) 추가
            current_item = {
                "item_symbol": enumerator.rstrip('.'),
                "item_text": content,
                "subitems": []
            }
            current_paragraph["items"].append(current_item)
            # Reset lower levels
            current_subitem = None
            continue

        # 4) 레벨 3 열거자 인식 (하드코딩된 리스트 사용)
        if any(line.startswith(symbol) for symbol in LEVEL3_ENUMS):
            for symbol in LEVEL3_ENUMS:
                if line.startswith(symbol):
                    content = line[len(symbol):].strip()
                    # 목(subitem) 추가
                    current_subitem = {
                        "subitem_symbol": symbol.rstrip('.'),
                        "subitem_text": content,
                        "subsubitems": []
                    }
                    if current_item:
                        current_item["subitems"].append(current_subitem)
                    break
            continue

        # 5) 레벨 4 열거자 인식 (동적 패턴 사용)
        match_level4 = LEVEL4_PATTERN.match(line)
        if match_level4 and current_subitem:
            enumerator = match_level4.group(0).strip()
            content = line[match_level4.end():].strip()
            # 하위목(subsubitem) 추가
            subsubitem = {
                "subsubitem_symbol": enumerator.rstrip(')'),
                "subsubitem_text": content
            }
            current_subitem["subsubitems"].append(subsubitem)
            continue

        # 6) 열거자 패턴에 매칭되지 않는 일반 텍스트 처리
        # 현재 컨텍스트에 따라 내용을 추가
        if current_article:
            if current_subitem and "subsubitem_text" in current_subitem:
                # 하위목 내용 추가
                current_subitem["subsubitem_text"] += " " + line
            elif current_subitem:
                # 하위목에 텍스트가 없는 경우
                current_subitem["subsubitem_text"] = line
            elif current_item and "item_text" in current_item:
                # 호 내용 추가
                current_item["item_text"] += " " + line
            elif current_paragraph and "paragraph_text" in current_paragraph:
                # 항 내용 추가
                current_paragraph["paragraph_text"] += " " + line
            elif current_article.get("article_text"):
                # 조 본문 내용 추가
                current_article["article_text"] += " " + line
            else:
                # 조 본문에 아직 내용이 없을 때 추가
                current_article["article_text"] = line

    # 모든 라인 처리 후, 현재 열린 조문을 추가
    if current_article:
        document["main_body"].append(current_article)

    return document

def convert_pdfs_to_json(folder_path, output_file):
    """
    Reads all PDFs in the given folder, parses them into structured JSON, 
    and writes the result to a JSON file.
    
    지정된 폴더의 모든 PDF 파일을 읽고, 파싱한 구조화 데이터를
    JSON 파일로 저장합니다.
    """
    documents = []
    for doc_id, file_name in enumerate(os.listdir(folder_path), start=1):
        if file_name.lower().endswith(".pdf"):
            pdf_path = os.path.join(folder_path, file_name)
            # 파일 이름에서 메타데이터 추출
            metadata = parse_filename(file_name)
            text = extract_text_from_pdf(pdf_path)
            if text:
                structured_data = parse_text_to_structure(
                    text, 
                    doc_id, 
                    metadata["document_title"]
                )
                # 메타데이터 추가
                structured_data["document_type"] = metadata["document_type"]
                structured_data["promulgation_number"] = metadata["promulgation_number"]
                structured_data["enforcement_date"] = metadata["enforcement_date"]
                documents.append(structured_data)

    with open(output_file, 'w', encoding='utf-8') as json_file:
        json.dump({"documents": documents}, json_file, indent=4, ensure_ascii=False)

    print(f"Processed {len(documents)} PDF(s). JSON saved to {output_file}")


if __name__ == "__main__":
    """
    Main entry point. 
    Usage: Just run this script; it will look for PDF files in 'pdfs' folder 
    and produce 'output.json'.
    
    이 스크립트의 메인 실행부입니다.
    'pdfs' 폴더 내의 PDF 파일을 모두 찾아 파싱한 뒤, 'output.json'으로 저장합니다.
    """
    folder_path = "pdfs"         # 폴더 경로
    output_file = "output.json"  # 결과를 저장할 JSON 파일명
    convert_pdfs_to_json(folder_path, output_file)