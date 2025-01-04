# PDF Legal Document Parser Report

## Table of Contents

1. [Introduction](#introduction)
2. [Project Overview](#project-overview)
3. [Code Structure](#code-structure)
    - [Enumerators and Patterns](#enumerators-and-patterns)
    - [Functions](#functions)
4. [Functionality](#functionality)
    - [Text Extraction](#text-extraction)
    - [Cleaning Unwanted Lines](#cleaning-unwanted-lines)
    - [Filename Parsing](#filename-parsing)
    - [Text Parsing and Structuring](#text-parsing-and-structuring)
    - [JSON Conversion and Saving](#json-conversion-and-saving)
5. [Usage Instructions](#usage-instructions)
6. [Examples](#examples)
    - [Example 1: Article with Enumerators](#example-1-article-with-enumerators)
    - [Example 2: Article without Enumerators](#example-2-article-without-enumerators)
    - [Example 3: Mixed Enumerators](#example-3-mixed-enumerators)
7. [Limitations](#limitations)
8. [Future Improvements](#future-improvements)
9. [Conclusion](#conclusion)

---

## Introduction

This report provides a comprehensive overview of a Python-based PDF parser designed to extract and structure legal documents. The parser efficiently handles various enumerator formats, ensuring accurate representation of hierarchical legal structures within PDF files. The final version of the code successfully manages scenarios where articles (조) may or may not contain enumerated paragraphs (항), addressing previous issues and enhancing reliability.

## Project Overview

Legal documents often follow a structured format with articles and paragraphs, sometimes incorporating different enumerator styles such as symbols (e.g., ①, ②) or numbers (e.g., 1항, 2항). Parsing these documents into a machine-readable format like JSON facilitates easier data manipulation, analysis, and integration into databases or applications.

The developed parser utilizes the `PyPDF2` library to extract text from PDFs and employs regular expressions to identify and structure different sections and enumerators within the documents.

## Code Structure

The parser is organized into several key components, each responsible for specific tasks in the extraction and structuring process.

### Enumerators and Patterns

1. **LEVEL1_ENUMS (Symbol-Based Enumerators):**
    ```python
    LEVEL1_ENUMS = [
        "①","②","③","④","⑤","⑥","⑦","⑧","⑨","⑩",
        "⑪","⑫","⑬","⑭","⑮","⑯","⑰","⑱","⑲","⑳",
        "㉑","㉒","㉓","㉔","㉕","㉖","㉗","㉘","㉙","㉚",
        "㉛","㉜","㉝","㉞","㉟"
    ]
    ```

2. **LEVEL3_ENUMS (Subitem Enumerators):**
    ```python
    LEVEL3_ENUMS = [
        "가.", "나.", "다.", "라.", "마.", "바.", "사.", "아.", "자.", "차."
    ]
    ```

3. **Dynamic Enumerator Patterns:**
    - **LEVEL2_PATTERN (Item Enumerators):**
        ```python
        LEVEL2_PATTERN = re.compile(r"^\d+\.\s*")    # Matches patterns like 1., 2., ..., 35.
        ```
    - **LEVEL4_PATTERN (Subsubitem Enumerators):**
        ```python
        LEVEL4_PATTERN = re.compile(r"^\d+\)\s*")    # Matches patterns like 1), 2), ..., 35)
        ```

4. **SECTION_PATTERN (Article Recognition):**
    ```python
    SECTION_PATTERN = re.compile(r"^제\s*(\d+조(?:의\d+)*)\s*\((.*?)\)\s*(.*)$")
    ```
    - **Description:** Recognizes articles formatted as `제n조(내용)` or `제n조의m(내용)`.

5. **LEVEL1_NUMBER_PATTERN (Number-Based Enumerators):**
    ```python
    LEVEL1_NUMBER_PATTERN = re.compile(r"^\d+항\s*")  # Matches patterns like 1항, 2항, ...
    ```

### Functions

1. **`extract_text_from_pdf(pdf_path)`**
    - **Purpose:** Extracts text content from a given PDF file using `PyPDF2`.
    - **Input:** Path to the PDF file.
    - **Output:** Extracted text as a single string or an empty string in case of an error.

2. **`clean_unwanted_lines(lines)`**
    - **Purpose:** Cleans the extracted text by removing headers, footers, page numbers, and other irrelevant lines.
    - **Input:** List of text lines.
    - **Output:** Cleaned list of lines.

3. **`parse_filename(file_name)`**
    - **Purpose:** Extracts metadata from the PDF filename using regular expressions.
    - **Input:** Filename string.
    - **Output:** Dictionary containing `document_title`, `document_type`, `promulgation_number`, and `enforcement_date`.

4. **`parse_text_to_structure(text, doc_id, title)`**
    - **Purpose:** Parses the cleaned text into a structured JSON format, identifying articles, paragraphs, and sub-items.
    - **Input:** Extracted text, document ID, and title.
    - **Output:** Structured dictionary representing the document's hierarchy.

5. **`convert_pdfs_to_json(folder_path, output_file)`**
    - **Purpose:** Processes all PDF files in the specified folder, parses them, and saves the structured data into a JSON file.
    - **Input:** Path to the folder containing PDFs and the desired output JSON filename.
    - **Output:** JSON file containing all parsed documents.

## Functionality

### Text Extraction

The parser utilizes the `PyPDF2` library to read and extract text from each page of a PDF document. It concatenates the text from all pages into a single string for further processing.

```python
def extract_text_from_pdf(pdf_path):
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
```

### Cleaning Unwanted Lines

Post extraction, the text is split into lines, and the `clean_unwanted_lines` function removes any lines that are likely to be headers, footers, or page numbers. This ensures that only relevant content is processed.

```python
def clean_unwanted_lines(lines):
    cleaned = []
    for line in lines:
        if "법제처" in line or "국가법령정보센터" in line:
            continue
        if line.strip().isdigit():
            continue
        cleaned.append(line)
    return cleaned
```

### Filename Parsing

The `parse_filename` function extracts metadata from the PDF filenames, assuming a specific naming convention. This metadata includes the document's title, type, promulgation number, and enforcement date.

```python
def parse_filename(file_name):
    base_name = os.path.splitext(file_name)[0]
    pattern = re.compile(r"^(.*?)\((.*?)\)\((.*?)\)\((\d{8})\)$")
    match = pattern.match(base_name)
    if match:
        return {
            "document_title": match.group(1).strip(),
            "document_type": match.group(2).strip(),
            "promulgation_number": match.group(3).strip(),
            "enforcement_date": match.group(4).strip()
        }
    else:
        print(f"Filename '{file_name}' does not match the expected pattern.")
        return {
            "document_title": base_name,
            "document_type": "",
            "promulgation_number": "",
            "enforcement_date": ""
        }
```

### Text Parsing and Structuring

The core function, `parse_text_to_structure`, processes each line of the cleaned text to identify and structure articles, paragraphs, items, and sub-items based on predefined enumerators and patterns.

- **Article Recognition:** Identifies articles using the `SECTION_PATTERN`. If an article contains additional content immediately after the article title, it checks whether it starts with an enumerator to determine if it should be treated as a paragraph or added directly to the article's text.

- **Paragraph Recognition:** Recognizes both symbol-based (e.g., `①`, `②`) and number-based (e.g., `1항`, `2항`) paragraphs. It creates a new paragraph entry within the current article.

- **Item and Subitem Recognition:** Identifies items (호) using `LEVEL2_PATTERN` and subitems (목) using `LEVEL3_ENUMS`. Further, it detects subsubitems (하위목) using `LEVEL4_PATTERN`.

- **General Text Handling:** Any text not matching enumerator patterns is appended to the appropriate section based on the current context (article, paragraph, item, or subitem).

```python
def parse_text_to_structure(text, doc_id, title):
    lines = text.split("\n")
    lines = clean_unwanted_lines(lines)

    document = {
        "document_id": str(doc_id),
        "document_title": title,
        "document_type": "",
        "promulgation_number": "",
        "enforcement_date": "",
        "main_body": []
    }

    current_article = None
    current_paragraph = None
    current_item = None
    current_subitem = None

    for line_number, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue

        # Article Recognition
        match_content = SECTION_PATTERN.match(line)
        if match_content:
            if current_article:
                document["main_body"].append(current_article)
            
            article_number = match_content.group(1)
            article_title = match_content.group(2)
            article_text = match_content.group(3).strip()

            current_article = {
                "article_number": article_number,
                "article_title": article_title,
                "article_text": article_text,
                "paragraphs": []
            }
            current_paragraph = None
            current_item = None
            current_subitem = None
            continue

        # Paragraph Recognition (Symbol-Based or Number-Based)
        level1_match = None
        symbol = None
        if any(line.startswith(sym) for sym in LEVEL1_ENUMS):
            for sym in LEVEL1_ENUMS:
                if line.startswith(sym):
                    symbol = sym
                    level1_match = sym
                    break
        else:
            match_number = LEVEL1_NUMBER_PATTERN.match(line)
            if match_number:
                symbol = match_number.group(0).strip()
                level1_match = symbol

        if level1_match:
            content = line[len(symbol):].strip()
            current_paragraph = {
                "paragraph_symbol": symbol,
                "paragraph_text": content,
                "items": []
            }
            current_article["paragraphs"].append(current_paragraph)
            current_item = None
            current_subitem = None
            continue

        # Item Recognition
        match_level2 = LEVEL2_PATTERN.match(line)
        if match_level2 and current_paragraph:
            enumerator = match_level2.group(0).strip()
            content = line[match_level2.end():].strip()
            current_item = {
                "item_symbol": enumerator.rstrip('.'),
                "item_text": content,
                "subitems": []
            }
            current_paragraph["items"].append(current_item)
            current_subitem = None
            continue

        # Subitem Recognition
        if any(line.startswith(sym) for sym in LEVEL3_ENUMS):
            for sym in LEVEL3_ENUMS:
                if line.startswith(sym):
                    content = line[len(sym):].strip()
                    current_subitem = {
                        "subitem_symbol": sym.rstrip('.'),
                        "subitem_text": content,
                        "subsubitems": []
                    }
                    if current_item:
                        current_item["subitems"].append(current_subitem)
                    break
            continue

        # Subsubitem Recognition
        match_level4 = LEVEL4_PATTERN.match(line)
        if match_level4 and current_subitem:
            enumerator = match_level4.group(0).strip()
            content = line[match_level4.end():].strip()
            subsubitem = {
                "subsubitem_symbol": enumerator.rstrip(')'),
                "subsubitem_text": content
            }
            current_subitem["subsubitems"].append(subsubitem)
            continue

        # General Text Handling
        if current_article:
            if current_subitem and "subsubitem_text" in current_subitem:
                current_subitem["subsubitem_text"] += " " + line
            elif current_subitem:
                current_subitem["subitem_text"] += " " + line
            elif current_item and "item_text" in current_item:
                current_item["item_text"] += " " + line
            elif current_paragraph and "paragraph_text" in current_paragraph:
                current_paragraph["paragraph_text"] += " " + line
            elif current_article.get("article_text"):
                current_article["article_text"] += " " + line
            else:
                current_article["article_text"] = line

    if current_article:
        document["main_body"].append(current_article)

    return document
```

### JSON Conversion and Saving

The `convert_pdfs_to_json` function orchestrates the entire process by iterating over all PDF files in the specified folder, extracting and parsing their content, and compiling the structured data into a single JSON file.

```python
def convert_pdfs_to_json(folder_path, output_file):
    documents = []
    for doc_id, file_name in enumerate(os.listdir(folder_path), start=1):
        if file_name.lower().endswith(".pdf"):
            pdf_path = os.path.join(folder_path, file_name)
            metadata = parse_filename(file_name)
            text = extract_text_from_pdf(pdf_path)
            if text:
                structured_data = parse_text_to_structure(
                    text, 
                    doc_id, 
                    metadata["document_title"]
                )
                # Add metadata
                structured_data["document_type"] = metadata["document_type"]
                structured_data["promulgation_number"] = metadata["promulgation_number"]
                structured_data["enforcement_date"] = metadata["enforcement_date"]
                documents.append(structured_data)

    with open(output_file, 'w', encoding='utf-8') as json_file:
        json.dump({"documents": documents}, json_file, indent=4, ensure_ascii=False)

    print(f"Processed {len(documents)} PDF(s). JSON saved to {output_file}")
```

## Usage Instructions

1. **Prerequisites:**
    - **Python 3.6+**: Ensure that Python is installed on your system.
    - **PyPDF2 Library**: Install via pip if not already installed.
        ```bash
        pip install PyPDF2
        ```

2. **Directory Setup:**
    - Create a folder named `pdfs` in the same directory as the script.
    - Place all the PDF files you wish to parse into the `pdfs` folder. Ensure that the filenames follow the expected pattern: `DocumentTitle(DocumentType)(PromulgationNumber)(EnforcementDate).pdf`, e.g., `방위사업관리규정(방위사업청훈령)(제864호)(20240711).pdf`.

3. **Running the Script:**
    - Execute the script using Python.
        ```bash
        python pdf_parser.py
        ```
    - Upon execution, the script will process all PDFs in the `pdfs` folder and generate an `output.json` file containing the structured data.

4. **Output:**
    - The `output.json` file will be created in the same directory as the script, containing all parsed documents in a structured JSON format.

## Examples

### Example 1: Article with Enumerators

**PDF Content:**
```
제8조(연구개발의 확대, 방산육성 및 국산화) 국방과학기술의 발전을 통한 자주국방을 실현하기 위하여 연구개발을 활성화하고 국산화와 민ㆍ군겸용 기술의 활용도를 높일 수 있도록 노력한다.
① 국방과학기술의 발전을 위한 기초연구 및 응용연구를 지원한다.
② 소요군은 국방과학기술 관련 교육 및 훈련을 강화한다.
```

**Filename:**
```
방위사업관리규정(방위사업청훈령)(제864호)(20240711).pdf
```

**Parsed JSON:**
```json
{
    "document_id": "1",
    "document_title": "방위사업관리규정",
    "document_type": "방위사업청훈령",
    "promulgation_number": "제864호",
    "enforcement_date": "20240711",
    "main_body": [
        {
            "article_number": "8조",
            "article_title": "연구개발의 확대, 방산육성 및 국산화",
            "article_text": "국방과학기술의 발전을 통한 자주국방을 실현하기 위하여 연구개발을 활성화하고 국산화와 민ㆍ군겸용 기술의 활용도를 높일 수 있도록 노력한다.",
            "paragraphs": [
                {
                    "paragraph_symbol": "①",
                    "paragraph_text": "국방과학기술의 발전을 위한 기초연구 및 응용연구를 지원한다.",
                    "items": []
                },
                {
                    "paragraph_symbol": "②",
                    "paragraph_text": "소요군은 국방과학기술 관련 교육 및 훈련을 강화한다.",
                    "items": []
                }
            ]
        }
    ]
}
```

### Example 2: Article without Enumerators

**PDF Content:**
```
제9조(군수지원) 국방력 강화를 위해 필요한 군수지원 및 관련 인프라를 구축한다.
```

**Filename:**
```
군수지원규정(군수지원청훈령)(제865호)(20240712).pdf
```

**Parsed JSON:**
```json
{
    "document_id": "2",
    "document_title": "군수지원규정",
    "document_type": "군수지원청훈령",
    "promulgation_number": "제865호",
    "enforcement_date": "20240712",
    "main_body": [
        {
            "article_number": "9조",
            "article_title": "군수지원",
            "article_text": "국방력 강화를 위해 필요한 군수지원 및 관련 인프라를 구축한다.",
            "paragraphs": []
        }
    ]
}
```

### Example 3: Mixed Enumerators

**PDF Content:**
```
제11조(군사교육) ① 군사교육의 질을 향상시킨다.
② 군사교육 프로그램을 확대한다.
3항 군사교육 관련 인프라를 구축한다.
```

**Filename:**
```
군사교육규정(군사청훈령)(제867호)(20240714).pdf
```

**Parsed JSON:**
```json
{
    "document_id": "4",
    "document_title": "군사교육규정",
    "document_type": "군사청훈령",
    "promulgation_number": "제867호",
    "enforcement_date": "20240714",
    "main_body": [
        {
            "article_number": "11조",
            "article_title": "군사교육",
            "article_text": "",
            "paragraphs": [
                {
                    "paragraph_symbol": "①",
                    "paragraph_text": "군사교육의 질을 향상시킨다.",
                    "items": []
                },
                {
                    "paragraph_symbol": "②",
                    "paragraph_text": "군사교육 프로그램을 확대한다.",
                    "items": []
                },
                {
                    "paragraph_symbol": "3항",
                    "paragraph_text": "군사교육 관련 인프라를 구축한다.",
                    "items": []
                }
            ]
        }
    ]
}
```

## Limitations

While the parser effectively handles the specified enumerator patterns and scenarios where articles may or may not contain enumerated paragraphs, there are certain limitations to be aware of:

1. **Filename Pattern Dependency:**
    - The parser relies on a specific filename pattern to extract metadata. Deviations from the expected pattern may result in incomplete or incorrect metadata extraction.

2. **Enumerator Patterns:**
    - Currently, the parser supports symbol-based enumerators (`①`, `②`, ...) and number-based enumerators (`1항`, `2항`). Other enumerator styles (e.g., letters, different numbering systems) are not recognized.

3. **Complex Nested Structures:**
    - The parser handles up to four levels of hierarchy (조, 항, 호, 목). More deeply nested structures or unconventional formats may not be accurately parsed.

4. **Error Handling:**
    - While basic error handling is implemented (e.g., logging filename pattern mismatches), more comprehensive error handling and logging mechanisms could enhance robustness.

## Future Improvements

To address the current limitations and enhance the parser's functionality, the following improvements are recommended:

1. **Enhanced Filename Parsing:**
    - Implement more flexible filename parsing to accommodate various naming conventions. This could include optional components or different ordering of metadata.

2. **Support for Additional Enumerator Patterns:**
    - Extend the parser to recognize and handle a wider variety of enumerator styles, such as alphabetical (e.g., `A.`, `B.`), Roman numerals (e.g., `I.`, `II.`), or custom symbols.

3. **Deeply Nested Structures:**
    - Modify the parsing logic to support deeper or more complex hierarchical structures beyond four levels, if required by the legal documents.

4. **Comprehensive Error Logging:**
    - Integrate a logging framework (e.g., Python's `logging` module) to record parsing errors, warnings, and informational messages. This facilitates easier debugging and monitoring.

5. **Unit Testing:**
    - Develop a suite of unit tests to validate the parser against a variety of PDF samples. Automated tests can ensure consistent performance and catch regressions during future modifications.

6. **User Configuration:**
    - Allow users to define or customize enumerator patterns and filename formats via configuration files or command-line arguments, increasing the parser's flexibility.

7. **Performance Optimization:**
    - Optimize the parser for handling large volumes of PDFs or very large documents, potentially through parallel processing or more efficient text handling techniques.

8. **GUI or CLI Enhancements:**
    - Develop a graphical user interface (GUI) or enhance the command-line interface (CLI) to provide a more user-friendly experience, including progress indicators and customizable settings.

## Conclusion

The developed PDF parser effectively transforms structured legal documents into a machine-readable JSON format, accommodating both symbol-based and number-based enumerators. By handling cases where articles may or may not contain enumerated paragraphs, the parser ensures versatility and reliability in processing diverse legal documents. While the current implementation meets the fundamental requirements, further enhancements can be pursued to increase its robustness, flexibility, and applicability to a broader range of document formats and structures.

---

If you encounter any further issues or require additional features, please feel free to reach out for assistance. Your feedback is invaluable in refining and improving the parser's capabilities.