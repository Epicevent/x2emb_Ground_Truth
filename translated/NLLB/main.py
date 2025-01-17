import json
from tqdm.auto import tqdm
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# -------------------------------------------------------------------------
# 1) Model & Tokenizer Setup
# -------------------------------------------------------------------------
model_name = "facebook/nllb-200-distilled-1.3B"
src_lang = "kor_Kore"
tgt_lang = "eng_Latn"

tokenizer = AutoTokenizer.from_pretrained(model_name)
base_model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

# Wrap in DataParallel to use both GPUs: [0,1]
model = torch.nn.DataParallel(base_model, device_ids=[0,1])
model = model.to("cuda:0")  # The main GPU device

def get_lang_token_id(tokenizer, lang_code):
    """
    Convert a language code into the special token ID used by NLLB.
    E.g., 'eng_Latn' -> tokenizer.convert_tokens_to_ids("<<eng_Latn>>")
    """
    return tokenizer.convert_tokens_to_ids(f"<<{lang_code}>>")

# -------------------------------------------------------------------------
# 2) Batch Translation Function
# -------------------------------------------------------------------------
def translate_batch(texts, src_language=src_lang, tgt_language=tgt_lang):
    """
    Translates a list of texts in one forward pass.
    This allows DataParallel to split the workload across 2 GPUs.
    """
    if not texts:
        return []

    # Prepend source language token to each text
    src_prefix = f"<<{src_language}>> "
    texts = [src_prefix + t if t else "" for t in texts]

    # Tokenize the entire batch
    inputs = tokenizer(
        texts,
        return_tensors="pt",
        max_length=512,
        truncation=True,
        padding=True  # important to enable batching
    ).to("cuda:0")

    forced_bos_token_id = get_lang_token_id(tokenizer, tgt_language)

    # Use model.module to access the underlying model for DataParallel
    generated_tokens = model.module.generate(
        **inputs,
        forced_bos_token_id=forced_bos_token_id,
        max_length=512,
        num_beams=4
    )

    # Decode each output in the batch
    translations = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)
    return translations

# -------------------------------------------------------------------------
# 3) JSON Field Extraction & Replacement
# -------------------------------------------------------------------------
def gather_texts_for_translation(data):
    """
    Iterates over the JSON and collects all translatable fields into a list.
    Also keeps track of *where* each piece of text should go (its "path").
    
    Returns:
        texts: List of strings to translate
        paths: Parallel list of 'paths' indicating the location of each text in the JSON
    """
    texts = []
    paths = []  # Will store (document_index, field_type, sub_index, ...)

    for doc_i, document in enumerate(data.get("documents", [])):
        # 문서 제목
        if document.get("document_title"):
            texts.append(document["document_title"])
            paths.append(("document_title_en", doc_i))

        for art_i, article in enumerate(document.get("main_body", [])):
            # 조 제목
            if article.get("article_title"):
                texts.append(article["article_title"])
                paths.append(("article_title_en", doc_i, art_i))

            # 조 본문
            if article.get("article_text"):
                texts.append(article["article_text"])
                paths.append(("article_text_en", doc_i, art_i))

            # 항(paragraph)
            for par_i, paragraph in enumerate(article.get("paragraphs", [])):
                if paragraph.get("paragraph_text"):
                    texts.append(paragraph["paragraph_text"])
                    paths.append(("paragraph_text_en", doc_i, art_i, par_i))

                # 항 내 아이템
                for item_i, item in enumerate(paragraph.get("items", [])):
                    if item.get("item_text"):
                        texts.append(item["item_text"])
                        paths.append(("item_text_en", doc_i, art_i, par_i, item_i))

                    # 하위 아이템(subitems)
                    for sub_i, subitem in enumerate(item.get("subitems", [])):
                        if subitem.get("subitem_text"):
                            texts.append(subitem["subitem_text"])
                            paths.append(("subitem_text_en", doc_i, art_i, par_i, item_i, sub_i))

                        # 더 깊은 수준(subsubitems)
                        for subsub_i, subsubitem in enumerate(subitem.get("subsubitems", [])):
                            if subsubitem.get("subsubitem_text"):
                                texts.append(subsubitem["subsubitem_text"])
                                paths.append(("subsubitem_text_en", doc_i, art_i, par_i, item_i, sub_i, subsub_i))

    return texts, paths

def place_translations_back(data, translations, paths):
    """
    Takes the list of translated texts and the parallel list of paths,
    and places each translation back into the correct location in 'data'.
    """
    for translation, path in zip(translations, paths):
        field_name = path[0]
        doc_i = path[1]

        # This is a bit manual. We need to parse how many levels deep we go:
        if len(path) == 2:
            # (field_name, doc_i)
            data["documents"][doc_i][field_name] = translation

        elif len(path) == 3:
            # (field_name, doc_i, art_i)
            art_i = path[2]
            data["documents"][doc_i]["main_body"][art_i][field_name] = translation

        elif len(path) == 4:
            # (field_name, doc_i, art_i, par_i)
            art_i = path[2]
            par_i = path[3]
            data["documents"][doc_i]["main_body"][art_i]["paragraphs"][par_i][field_name] = translation

        elif len(path) == 5:
            # (field_name, doc_i, art_i, par_i, item_i)
            art_i = path[2]
            par_i = path[3]
            item_i = path[4]
            data["documents"][doc_i]["main_body"][art_i]["paragraphs"][par_i]["items"][item_i][field_name] = translation

        elif len(path) == 6:
            # (field_name, doc_i, art_i, par_i, item_i, sub_i)
            art_i = path[2]
            par_i = path[3]
            item_i = path[4]
            sub_i = path[5]
            data["documents"][doc_i]["main_body"][art_i]["paragraphs"][par_i]["items"][item_i]["subitems"][sub_i][field_name] = translation

        elif len(path) == 7:
            # (field_name, doc_i, art_i, par_i, item_i, sub_i, subsub_i)
            art_i = path[2]
            par_i = path[3]
            item_i = path[4]
            sub_i = path[5]
            subsub_i = path[6]
            data["documents"][doc_i]["main_body"][art_i]["paragraphs"][par_i]["items"][item_i]["subitems"][sub_i]["subsubitems"][subsub_i][field_name] = translation

        else:
            raise ValueError(f"Unhandled path structure: {path}")

# -------------------------------------------------------------------------
# 4) Main Translation Logic (Chunking)
# -------------------------------------------------------------------------
def translate_json_in_chunks(input_file, output_file, chunk_size=16):
    """
    1) Read JSON
    2) Gather all translatable texts into a big list
    3) Translate them in mini-batches (chunks) so DataParallel can use both GPUs
    4) Place translations back
    5) Save JSON
    """
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Gather all texts and track their "paths"
    texts, paths = gather_texts_for_translation(data)
    print(f"Found {len(texts)} text fields to translate.")

    # We'll translate in chunks
    all_translations = []
    pbar = tqdm(total=len(texts), desc="Translating", unit="fields")

    for i in range(0, len(texts), chunk_size):
        chunk = texts[i:i+chunk_size]
        # Translate this batch
        translations = translate_batch(chunk)
        all_translations.extend(translations)
        pbar.update(len(chunk))

    pbar.close()

    # Now place them back in the data structure
    place_translations_back(data, all_translations, paths)

    # Save the translated file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"Done. Translated JSON saved to: {output_file}")

# -------------------------------------------------------------------------
# 5) Run
# -------------------------------------------------------------------------
if __name__ == "__main__":
    input_json = "../../output.json"
    output_json = "translatedNLLB.json"
    translate_json_in_chunks(input_json, output_json, chunk_size=4)
