import re
import json
import os
import sys
import olefile



###########################################
# 2) Extract text from a .hwp (no PDF!)   #
###########################################
def extract_text_from_hwp(hwp_path):
    reader = HWPReader(hwp_path)
    text = reader.get_text()
    return text.strip() if text else ""




VALID_LINE_PATTERN = re.compile(
    r"^"                             
    r"(?:"
    # (A) "제 n (장 | 절 | 조 (의 n)?)"
    #     This handles "제1장", "제2절", "제3조", "제3조의2", etc.
    r"제\s*\d+(?:장|절|조(?:의\d+)?)"
    r"|"
    # (B) Numeric enumerators, e.g. "1.", "2.", "10.", etc.
    r"\d+\.\s*"
    r"|"
    # (C) Hangul enumerators: "가.", "나.", ...
    r"[가나다라마바사아자차카타파하]\.\s*"
    r"|"
    # (D) Parenthesis enumerators: ①~㉟
    r"[①-㉟]"
    r")"
)

def is_valid_line(line: str) -> bool:
    return bool(VALID_LINE_PATTERN.match(line.strip()))


def split_jomun_list_and_main_text(full_text, marker="{전문}"):
    """
    Splits 'full_text' into two parts, using 'marker' to indicate 
    where the 조문목록 ends and the main text (본문) begins.
    """
    lines = full_text.split("\n")
    jomun_list_lines = []
    main_text_lines = []
    
    found_marker = False
    for line in lines:
        if not found_marker:
            # We haven’t seen "{전문}" yet
            if line.strip() == marker:
                found_marker = True
            else:
                jomun_list_lines.append(line)
        else:
            # After "{전문}"
            main_text_lines.append(line)
    
    jomun_list_text = "\n".join(jomun_list_lines)
    main_text = "\n".join(main_text_lines)
    return jomun_list_text, main_text

def extract_valid_lines(text: str):
    """
    Splits text by newline and keeps only valid lines 
    (based on is_valid_line).
    """
    kept = []
    for ln in text.split("\n"):
        ln_str = ln.strip()
        if ln_str and is_valid_line(ln_str):
            kept.append(ln_str)
    return kept


ARTICLE_LIST_PATTERN = re.compile(r"^제\s*(\d+조(?:의\d+)?)(?:\(([^)]*)\))?")

def extract_article_numbers_from_jomun(jomun_lines):
    """
    Given a list of lines for the 조문목록 (already filtered for validity),
    returns a set of article numbers like {"1조", "67조", "67조의2", ...}.
    """
    article_numbers = set()
    for line in jomun_lines:
        match = ARTICLE_LIST_PATTERN.match(line)
        if match:
            # group(1) = "1조" or "67조" or "67조의2", etc.
            art_num = match.group(1)
            article_numbers.add(art_num)
    return article_numbers

###############################################
# B) Parsing the 본문 with your actual parser #
###############################################
# This is a trivial example. Replace with your real parse_text_to_structure().
SECTION_REGEX = re.compile(r"^제\s*(\d+조(?:의\d+)?)\s*\((.*?)\)\s*(.*)$")

def parse_text_to_structure(lines, doc_id, title):
    """
    Example parser that processes a list of lines (already filtered),
    looking for "제n조(…)" patterns. 
    Replace with your advanced enumerator-handling version as needed.
    """
    document = {
        "document_id": str(doc_id),
        "document_title": title,
        "main_body": []
    }
    
    current_article = None
    for line in lines:
        line = line.strip()
        # Match "제n조(…)" or "제n조의m(...)"
        match_sec = SECTION_REGEX.match(line)
        if match_sec:
            # If we had a previous article, store it
            if current_article:
                document["main_body"].append(current_article)
            
            article_number = match_sec.group(1)  # e.g. "67조", "67조의2"
            article_title  = match_sec.group(2)  # e.g. "탐색개발기본계획서 작성 등"
            extra_text     = match_sec.group(3).strip()
            
            current_article = {
                "article_number": article_number,
                "article_title": article_title,
                "article_text": extra_text
            }
        else:
            # Continuation of the current article text
            if current_article:
                current_article["article_text"] += " " + line
    
    # If there's a last article in progress, append it
    if current_article:
        document["main_body"].append(current_article)
    
    return document

#########################################
# C) Compare 조문목록 vs. Parser Output #
#########################################
def compare_jomun_and_parsed(jomun_article_nums, parsed_document):
    """
    Compares the set of article numbers from the 조문목록 to the parser's 
    recognized articles in 'parsed_document'.
    """
    # Gather recognized articles
    recognized_nums = set()
    for art in parsed_document.get("main_body", []):
        recognized_nums.add(art["article_number"])
    
    # Missing: in 조문목록 but not recognized
    missing = jomun_article_nums - recognized_nums
    # Extra: recognized by parser but not in 조문목록
    extra = recognized_nums - jomun_article_nums
    
    return missing, extra

#########################################
# D) Putting It All Together (Step 3)   #
#########################################
def step3_test_parser(jomun_lines, main_lines):
    """
    1) Extract article numbers from 조문목록 lines.
    2) Parse the main lines with parse_text_to_structure().
    3) Compare the results.
    4) Print a summary.
    """
    # 1) 조문목록 article numbers
    jomun_article_nums = extract_article_numbers_from_jomun(jomun_lines)
    
    # 2) Parse 본문
    doc_id = 1
    title = "방위사업관리규정(테스트)"
    parsed_doc = parse_text_to_structure(main_lines, doc_id, title)
    
    # 3) Compare
    missing, extra = compare_jomun_and_parsed(jomun_article_nums, parsed_doc)
    
    # 4) Print results
    print("=== Parsed Document ===")
    print(json.dumps(parsed_doc, ensure_ascii=False, indent=4))
    
    print("\n=== Comparison Results ===")
    print("조문목록 기사들:", sorted(jomun_article_nums))
    recognized_nums = [art["article_number"] for art in parsed_doc["main_body"]]
    print("파서 인식 기사들:", recognized_nums)
    if missing:
        print(f"[MISSING] The parser didn't recognize: {missing}")
    else:
        print("[OK] No missing articles.")
    if extra:
        print(f"[EXTRA] The parser recognized extra articles not in 조문목록: {extra}")
    else:
        print("[OK] No extra articles.")

#####################
# Example usage
#####################
if __name__ == "__main__":
    path = "/content/file_name.hwp"
    f = olefile.OleFileIO(path)
    print(f.listdir())
    # --- 1) Extract full text from HWP ---
    full_text = extract_text_from_hwp(hwp_file)
    if not full_text:
        print("[ERROR] No text extracted from the HWP.")
        sys.exit(1)


    # Finally, run the step 3 test:
    step3_test_parser(jomun_list_kept, main_text_kept)