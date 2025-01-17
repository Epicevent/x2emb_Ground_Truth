import json
import torch
import threading
from tqdm.auto import tqdm
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

model_name = "facebook/nllb-200-distilled-1.3B"

# Load 2 copies of the model, each on a different GPU
model_gpu0 = AutoModelForSeq2SeqLM.from_pretrained(model_name).to("cuda:0")
model_gpu1 = AutoModelForSeq2SeqLM.from_pretrained(model_name).to("cuda:1")

# Create TWO separate tokenizer objects
tokenizer_gpu0 = AutoTokenizer.from_pretrained(model_name)
tokenizer_gpu1 = AutoTokenizer.from_pretrained(model_name)

def get_lang_token_id(tokenizer, lang_code):
    return tokenizer.convert_tokens_to_ids(f"<<{lang_code}>>")

def translate_sublist(
    sublist,
    results_dict,
    model,
    tokenizer,
    device,
    batch_size=8,
    src_lang="kor_Kore",
    tgt_lang="eng_Latn",
):
    """
    Translates all (idx, text, path) items in 'sublist' on the specified 'device',
    storing results in 'results_dict[idx] = translated_text'.
    Each thread has its own 'tokenizer'.
    """
    prefix = f"<<{src_lang}>> "

    for i in range(0, len(sublist), batch_size):
        batch_chunk = sublist[i : i + batch_size]
        raw_texts = [prefix + x[1] if x[1] else "" for x in batch_chunk]  # x[1] = text

        inputs = tokenizer(
            raw_texts,
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

        translations = tokenizer.batch_decode(outputs, skip_special_tokens=True)

        for (orig_idx, _, _), trans in zip(batch_chunk, translations):
            results_dict[orig_idx] = trans

def gather_texts(data):
    """
    Gather *all* translatable text fields, returning a list of (index, text, path).
    'index' is a unique integer so we can reassemble the final output in correct order.
    'path' is a tuple describing where to place the translation in the JSON.
    """
    items = []
    current_idx = 0

    for doc_i, document in enumerate(data.get("documents", [])):
        # document_title
        if document.get("document_title"):
            items.append((current_idx, document["document_title"], ("document_title_en", doc_i)))
            current_idx += 1

        for art_i, article in enumerate(document.get("main_body", [])):
            # article_title
            if article.get("article_title"):
                items.append((current_idx, article["article_title"], ("article_title_en", doc_i, art_i)))
                current_idx += 1

            # article_text
            if article.get("article_text"):
                items.append((current_idx, article["article_text"], ("article_text_en", doc_i, art_i)))
                current_idx += 1

            # paragraphs
            for par_i, paragraph in enumerate(article.get("paragraphs", [])):
                if paragraph.get("paragraph_text"):
                    items.append((current_idx, paragraph["paragraph_text"], ("paragraph_text_en", doc_i, art_i, par_i)))
                    current_idx += 1

                # items
                for item_i, item in enumerate(paragraph.get("items", [])):
                    if item.get("item_text"):
                        items.append((current_idx, item["item_text"], ("item_text_en", doc_i, art_i, par_i, item_i)))
                        current_idx += 1

                    # subitems
                    for sub_i, subitem in enumerate(item.get("subitems", [])):
                        if subitem.get("subitem_text"):
                            items.append((current_idx, subitem["subitem_text"], ("subitem_text_en", doc_i, art_i, par_i, item_i, sub_i)))
                            current_idx += 1

                        # subsubitems
                        if "subsubitems" in subitem:
                            for subsub_i, subsubitem in enumerate(subitem["subsubitems"]):
                                if subsubitem.get("subsubitem_text"):
                                    items.append((
                                        current_idx,
                                        subsubitem["subsubitem_text"],
                                        ("subsubitem_text_en", doc_i, art_i, par_i, item_i, sub_i, subsub_i)
                                    ))
                                    current_idx += 1

    return items

def place_translations(data, indexed_items, final_translations):
    """
    Re-inserts translations (found in final_translations[idx]) back into 'data'
    according to each path in 'indexed_items'.
    """
    for (idx, _, path) in indexed_items:
        translation = final_translations.get(idx, "")
        field_name = path[0]
        doc_i = path[1]

        if len(path) == 2:
            data["documents"][doc_i][field_name] = translation
        elif len(path) == 3:
            art_i = path[2]
            data["documents"][doc_i]["main_body"][art_i][field_name] = translation
        elif len(path) == 4:
            art_i = path[2]
            par_i = path[3]
            data["documents"][doc_i]["main_body"][art_i]["paragraphs"][par_i][field_name] = translation
        elif len(path) == 5:
            art_i = path[2]
            par_i = path[3]
            item_i = path[4]
            data["documents"][doc_i]["main_body"][art_i]["paragraphs"][par_i]["items"][item_i][field_name] = translation
        elif len(path) == 6:
            art_i = path[2]
            par_i = path[3]
            item_i = path[4]
            sub_i = path[5]
            data["documents"][doc_i]["main_body"][art_i]["paragraphs"][par_i]["items"][item_i]["subitems"][sub_i][field_name] = translation
        elif len(path) == 7:
            art_i = path[2]
            par_i = path[3]
            item_i = path[4]
            sub_i = path[5]
            subsub_i = path[6]
            data["documents"][doc_i]["main_body"][art_i]["paragraphs"][par_i]["items"][item_i]["subitems"][sub_i]["subsubitems"][subsub_i][field_name] = translation
        else:
            raise ValueError(f"Unhandled path structure: {path}")

def main():
    input_json = "../../output.json"
    output_json = "translatedNLLB.json"

    # 1) Load JSON
    with open(input_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 2) Gather text
    indexed_items = gather_texts(data)
    n_items = len(indexed_items)
    print(f"Found {n_items} fields to translate.")

    # 3) Split the list into 2 sublists (GPU0, GPU1)
    half = n_items // 2
    sublist_gpu0 = indexed_items[:half]
    sublist_gpu1 = indexed_items[half:]

    print(f"GPU0 has {len(sublist_gpu0)} items, GPU1 has {len(sublist_gpu1)} items.")

    # 4) Shared dictionary for results
    translations_dict = {}

    # 5) Two threads, each with a separate tokenizer
    t0 = threading.Thread(
        target=translate_sublist,
        args=(sublist_gpu0, translations_dict, model_gpu0, tokenizer_gpu0, "cuda:0")
    )
    t1 = threading.Thread(
        target=translate_sublist,
        args=(sublist_gpu1, translations_dict, model_gpu1, tokenizer_gpu1, "cuda:1")
    )

    # 6) Start both threads
    t0.start()
    t1.start()

    # 7) Wait for them to finish
    t0.join()
    t1.join()

    # 8) Place translations back
    place_translations(data, indexed_items, translations_dict)

    # 9) Save final JSON
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print("Done. Output saved to:", output_json)

if __name__ == "__main__":
    main()
