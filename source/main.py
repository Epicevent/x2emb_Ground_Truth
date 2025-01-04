import os
import json
from PyPDF2 import PdfReader
import re

# 1) A set of valid higher-level enumerator characters (① ~ ㉟)
#    'ㆍ' is *not* included, so it won't be interpreted as an enumerator.
# 1) 상위 열거자로 인정할 문자를 모아둔 세트 (① ~ ㉟)
#    'ㆍ'는 포함되지 않았으므로 열거자로 처리되지 않습니다.
VALID_HIGHER_ENUMS = {
    "①","②","③","④","⑤","⑥","⑦","⑧","⑨","⑩",
    "⑪","⑫","⑬","⑭","⑮","⑯","⑰","⑱","⑲","⑳",
    "㉑","㉒","㉓","㉔","㉕","㉖","㉗","㉘","㉙","㉚",
    "㉛","㉜","㉝","㉞","㉟"
}

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

def is_higher_level_enum(s):
    """
    Checks if the first character is one of our valid enumerator symbols.
    문자열의 첫 글자가 VALID_HIGHER_ENUMS에 속하는지 확인하여
    상위 열거자로 처리할지 결정합니다.
    """
    return bool(s) and (s[0] in VALID_HIGHER_ENUMS)

def clean_unwanted_lines(lines):
    """
    Removes lines that seem to be headers/footers or purely numeric (page numbers).
    '법제처', '국가법령정보센터' 등이 포함된 라인 또는 페이지 번호(숫자만 있는 라인)를 제거합니다.
    """
    cleaned = []
    for line in lines:
        # Skip lines with '법제처' or '국가법령정보센터'
        # '법제처' 혹은 '국가법령정보센터'가 포함된 라인은 제외
        if "법제처" in line or "국가법령정보센터" in line:
            continue
        
        # Skip purely numeric lines (likely page numbers)
        # 순수 숫자로만 구성된 라인은 페이지 번호로 가정하고 제외
        if line.strip().isdigit():
            continue
        
        cleaned.append(line)
    return cleaned

def parse_text_to_structure(text, doc_id, title):
    """
    Parses the extracted text into a structured JSON format.
    - Skips unwanted lines (headers/footers).
    - Identifies sections with '제n조(...)'.
    - Splits out enumerators: 
        * higher-level (e.g. '①') restricted to VALID_HIGHER_ENUMS
        * lower-level (e.g. '1.')
    - Accumulates multi-line content under the correct enumerator/section.

    추출된 텍스트를 구조화된 JSON 형식으로 파싱합니다.
    - 헤더/푸터로 보이는 라인을 제거합니다.
    - '제n조(...)' 형태를 섹션으로 구분합니다.
    - VALID_HIGHER_ENUMS에 해당하는 상위 열거자(①, ②, ...)와
      '1.' 형식의 하위 열거자를 분리 처리합니다.
    - 여러 줄에 걸쳐 분산된 내용을 올바른 열거자/섹션에 쌓아갑니다.
    """

    # Split text into lines, then remove known headers/footers
    # 텍스트를 줄 단위로 분할 후, 알려진 헤더/푸터를 제거합니다.
    lines = text.split("\n")
    lines = clean_unwanted_lines(lines)

    sections = []
    current_section = None
    current_higher_level = None

    # Pattern for '제n조(...)' at the start of a line
    # 라인의 시작에서 '제n조(...)' 패턴을 찾기 위한 정규표현식
    section_pattern = re.compile(r"^제(\d+조(?:의\d+)?)\((.*?)\)")

    # Pattern for lower-level enumerators like '1.', '2.', etc.
    # '1.', '2.' 형식의 하위 열거자 정규표현식
    lower_level_pattern = re.compile(r"^\d+\.")

    def process_remainder(remainder_text):
        """
        Recursively (or iteratively) parse any leftover text in the line
        to find enumerators (higher and lower) or content.
        
        줄에 남은 텍스트를 열거자(상위/하위) 또는 본문으로 파싱합니다.
        """
        nonlocal current_section, current_higher_level
        
        remainder_text = remainder_text.strip()
        if not remainder_text:
            return
        
        while remainder_text:
            # A) Check if the first character is a valid higher-level enumerator (e.g. '③')
            # A) 남은 문자열의 첫 글자가 유효한 상위 열거자(예: '③')인지 확인
            if is_higher_level_enum(remainder_text):
                # Close the old higher_level if open
                # 기존에 열린 상위 열거자를 섹션에 추가
                if current_higher_level and current_section:
                    current_section["higher_levels"].append(current_higher_level)
                    current_higher_level = None

                # enumerator_symbol is the first character of remainder_text
                # 남은 문자열의 첫 글자(예: '③')
                enumerator_symbol = remainder_text[0]

                # Everything after that symbol is the content remainder
                # 열거자 기호 뒤의 내용을 추출
                remainder_text = remainder_text[1:].strip()

                # Create a new higher-level entry
                # 새로운 상위 열거자 구조체 생성
                current_higher_level = {
                    "level": enumerator_symbol,
                    "content": "",
                    "lower_levels": []
                }

            # B) Check if we have a lower-level enumerator at the start (e.g. '1.')
            # B) 남은 문자열이 하위 열거자(1., 2., ...)로 시작하는지 확인
            elif lower_level_pattern.match(remainder_text):
                lower_match = lower_level_pattern.match(remainder_text)
                if lower_match:
                    # If no higher_level is open, create one (virtual)
                    # 상위 열거자가 없으면 임시로 생성
                    if not current_higher_level:
                        if not current_section:
                            current_section = {
                                "title": "Untitled Section",
                                "higher_levels": []
                            }
                        current_higher_level = {
                            "level": "",
                            "content": "",
                            "lower_levels": []
                        }
                    
                    # e.g., '1.' -> sublevel_num = '1'
                    sublevel_num = lower_match.group(0).replace(".", "")
                    offset = len(lower_match.group(0))
                    
                    # Remainder after removing '1.'
                    content_after_sub = remainder_text[offset:].strip()
                    
                    # Create a new lower-level item
                    # 새로운 하위 열거자 항목을 생성
                    current_higher_level["lower_levels"].append({
                        "sublevel": sublevel_num,
                        "content": ""
                    })
                    
                    # Update remainder_text to parse next enumerator or content
                    # 하위 열거자 뒤 남은 텍스트를 계속 파싱하기 위해 remainder_text 갱신
                    remainder_text = content_after_sub

            else:
                # C) No enumerator found at the start -> treat this chunk as content
                # C) 열거자(상위/하위)가 아니라면 본문으로 처리
                #    But we also need to see if there's another enumerator soon in the text.
                
                # Find the earliest occurrence of a valid enumerator or lower-level
                # 이후에 나올 상/하위 열거자의 위치를 찾아서 content를 분할
                possible_indices = []

                # 1) Check for next lower-level enumerator (regex)
                lm = lower_level_pattern.search(remainder_text)
                if lm:
                    possible_indices.append(lm.start())

                # 2) Check for next higher-level enumerator from VALID_HIGHER_ENUMS
                #    Scan each char in remainder_text
                for i, ch in enumerate(remainder_text):
                    if ch in VALID_HIGHER_ENUMS:
                        possible_indices.append(i)

                # If we found a future enumerator, split the text at that point
                # 열거자가 나오는 위치가 있다면, 그 전까지의 텍스트를 현재 content로 취급
                if possible_indices:
                    next_index = min(possible_indices)
                    content_part = remainder_text[:next_index].strip()
                else:
                    next_index = None
                    content_part = remainder_text.strip()
                
                # Append this content to the current higher-level or create one if needed
                # 현재 상위 열거자에 내용 추가 (없으면 생성)
                if current_higher_level:
                    if current_higher_level["lower_levels"]:
                        # If there's at least one sub-level open, append to the last sub-level
                        current_higher_level["lower_levels"][-1]["content"] += " " + content_part
                    else:
                        # Otherwise, append to the higher-level's own content
                        current_higher_level["content"] += " " + content_part
                else:
                    # If no higher_level, create a 'virtual' one
                    if not current_section:
                        current_section = {
                            "title": "Untitled Section",
                            "higher_levels": []
                        }
                    if not current_higher_level:
                        current_higher_level = {
                            "level": "",
                            "content": content_part,
                            "lower_levels": []
                        }
                    else:
                        current_higher_level["content"] += " " + content_part
                
                if next_index is None:
                    # No more enumerators -> done with this remainder
                    remainder_text = ""
                else:
                    # Move remainder_text to next enumerator boundary
                    remainder_text = remainder_text[next_index:].strip()

    # --- MAIN PARSE LOGIC: line by line
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if the line starts with '제n조(...)'
        match_section = section_pattern.match(line)
        if match_section:
            # Close the previously open section if any
            if current_section:
                if current_higher_level:
                    current_section["higher_levels"].append(current_higher_level)
                    current_higher_level = None
                sections.append(current_section)
            
            # Create a new section
            section_title =match_section.group().strip()
            current_section = {
                "title": section_title,
                "higher_levels": []
            }
            
            # Process the remainder of the line beyond '제n조(...)'
            remainder_text = line[match_section.end():]
            if remainder_text:
                process_remainder(remainder_text)

        else:
            # If not a section start, process for enumerators/content
            process_remainder(line)

    # After processing all lines, close any remaining open structures
    if current_higher_level and current_section:
        current_section["higher_levels"].append(current_higher_level)
    if current_section:
        sections.append(current_section)

    return {
        "id": str(doc_id),
        "title": title,
        "sections": sections
    }

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
            text = extract_text_from_pdf(pdf_path)
            if text:
                structured_data = parse_text_to_structure(
                    text, 
                    doc_id, 
                    file_name.replace(".pdf", "")
                )
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
