import json
import torch
from tqdm.auto import tqdm
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

model_name = "facebook/nllb-200-distilled-1.3B"

# 2 copies, each on different GPU
model_gpu0 = AutoModelForSeq2SeqLM.from_pretrained(model_name).to("cuda:0")
model_gpu1 = AutoModelForSeq2SeqLM.from_pretrained(model_name).to("cuda:1")

tokenizer = AutoTokenizer.from_pretrained(model_name)

def get_lang_token_id(tokenizer, lang_code):
    return tokenizer.convert_tokens_to_ids(f"<<{lang_code}>>")

def translate_batch(texts, model, tokenizer, src_lang="kor_Kore", tgt_lang="eng_Latn", device="cuda:0"):
    if not texts:
        return []
    prefix = f"<<{src_lang}>> "
    texts = [prefix + t if t else "" for t in texts]

    inputs = tokenizer(
        texts,
        return_tensors="pt",
        max_length=512,
        padding=True,
        truncation=True
    ).to(device)

    forced_bos_token_id = get_lang_token_id(tokenizer, tgt_lang)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            forced_bos_token_id=forced_bos_token_id,
            max_length=512,
            num_beams=4
        )

    return tokenizer.batch_decode(outputs, skip_special_tokens=True)

def split_list(lst, n):
    k, m = divmod(len(lst), n)
    return [lst[i*k+min(i,m):(i+1)*k+min(i+1,m)] for i in range(n)]

# -------------- EXTRACT + REINSERT UTILS --------------
def gather_texts(data):
    """
    Returns (texts, paths), where:
      texts: A list of strings to translate.
      paths: A parallel list describing where each text came from.
    """
    texts = []
    paths = []
    for doc_i, document in enumerate(data.get("documents", [])):
        if "document_title" in document:
            texts.append(document["document_title"])
            paths.append(("document_title_en", doc_i))

        for art_i, article in enumerate(document.get("main_body", [])):
            if "article_title" in article:
                texts.append(article["article_title"])
                paths.append(("article_title_en", doc_i, art_i))
            # ... keep going for article_text, paragraphs, items, etc.

    return texts, paths

def place_translations(data, translations, paths):
    """
    Puts 'translations' back into 'data' using 'paths'
    so that the new fields appear in the JSON.
    """
    for t, p in zip(translations, paths):
        field_name = p[0]
        doc_i = p[1]

        if len(p) == 2:
            data["documents"][doc_i][field_name] = t
        elif len(p) == 3:
            art_i = p[2]
            data["documents"][doc_i]["main_body"][art_i][field_name] = t
        # etc. for deeper levels

def main():
    input_file = "../../output.json"
    output_file = "translatedNLLB.json"

    # Load the nested JSON (dictionary)
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Extract all translatable text from the nested structure
    texts, paths = gather_texts(data)

    # Split the text list into GPU0 and GPU1 chunks
    chunked = split_list(texts, 2)
    texts_gpu0 = chunked[0]
    texts_gpu1 = chunked[1] if len(chunked) > 1 else []

    print(f"GPU0: {len(texts_gpu0)} texts; GPU1: {len(texts_gpu1)} texts")

    # Translate chunk #1 on GPU0
    translations_gpu0 = []
    batch_size = 8
    for i in tqdm(range(0, len(texts_gpu0), batch_size), desc="GPU0"):
        batch = texts_gpu0[i:i+batch_size]
        out = translate_batch(batch, model_gpu0, tokenizer, device="cuda:0")
        translations_gpu0.extend(out)

    # Translate chunk #2 on GPU1
    translations_gpu1 = []
    for i in tqdm(range(0, len(texts_gpu1), batch_size), desc="GPU1"):
        batch = texts_gpu1[i:i+batch_size]
        out = translate_batch(batch, model_gpu1, tokenizer, device="cuda:1")
        translations_gpu1.extend(out)

    # Combine in same order
    final_translations = translations_gpu0 + translations_gpu1

    # Put them back into the JSON structure
    place_translations(data, final_translations, paths)

    # Save updated data
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print("Done.")

if __name__ == "__main__":
    main()
