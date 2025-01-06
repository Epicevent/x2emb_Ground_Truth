import json

def generate_chunks_from_document(doc_json):
    chunks = []
    
    # Document-level metadata
    doc_id = doc_json.get("document_id")
    document_title = doc_json.get("document_title")
    
    # Iterate through main body (articles)
    for article in doc_json.get("main_body", []):
        article_number = article.get("article_number")
        article_title = article.get("article_title")
        article_text = article.get("article_text", "").strip()
        
        # Create a chunk for the entire article (large chunk)
        if article_text:
            chunks.append({
                "chunk_id": f"doc{doc_id}_{article_number}",
                "embedding_text": f"{document_title} {article_number} {article_text}"
            })
        
        # Iterate through paragraphs (small chunks)
        for paragraph in article.get("paragraphs", []):
            paragraph_symbol = paragraph.get("paragraph_symbol")
            paragraph_text = paragraph.get("paragraph_text", "").strip()
            
            if paragraph_text:
                chunks.append({
                    "chunk_id": f"doc{doc_id}_{article_number}_{paragraph_symbol}",
                    "embedding_text": paragraph_text
                })
    
    return chunks

# Example usage
doc_json = {
    "document_id": "1",
    "document_title": "방위사업관리규정",
    "main_body": [
        {
            "article_number": "8조",
            "article_title": "연구개발의 확대, 방산육성 및 국산화",
            "article_text": "국방과학기술의 발전을 통한 자주국방을 실현하기 위하여 연구개발을 활성화하고 국산화와 민ㆍ군겸용 기술의 활용도를 높일 수 있도록 노력한다.",
            "paragraphs": [
                {
                    "paragraph_symbol": "①",
                    "paragraph_text": "국방과학기술의 발전을 위한 기초연구 및 응용연구를 지원한다."
                },
                {
                    "paragraph_symbol": "②",
                    "paragraph_text": "소요군은 국방과학기술 관련 교육 및 훈련을 강화한다."
                }
            ]
        }
    ]
}

# Generate chunks
chunks = generate_chunks_from_document(doc_json)

# Save chunks to JSON file
with open("chunks.json", "w", encoding="utf-8") as f:
    json.dump(chunks, f, indent=4, ensure_ascii=False)

# Print result
print(json.dumps(chunks, indent=4, ensure_ascii=False))
