import json

# Define a dictionary of critical terms and their expected translations
TERMS = {
    "육군": "Army",
    "해군": "Navy",
    "공군": "Air Force",
    "합동참모본부": "Joint Chiefs of Staff",
    "방위사업청": "Defense Acquisition Program Administration"
}

# Function to evaluate translation quality
def evaluate_translation(original_file, translated_file, output_file):
    with open(original_file, 'r', encoding='utf-8') as orig_f, open(translated_file, 'r', encoding='utf-8') as trans_f:
        original_data = json.load(orig_f)
        translated_data = json.load(trans_f)

    mismatches = []
    total_phrases = 0
    correct_phrases = 0

    for orig_chunk, trans_chunk in zip(original_data["chunks"], translated_data["chunks"]):
        if orig_chunk.get("content") and trans_chunk.get("content"):
            original_text = orig_chunk["content"]
            translated_text = trans_chunk["content"]

            # Check if critical terms are correctly translated
            for term, expected_translation in TERMS.items():
                if term in original_text:
                    total_phrases += 1
                    if expected_translation not in translated_text:
                        mismatches.append({
                            "original": original_text,
                            "translated": translated_text,
                            "missing_term": term,
                            "expected_translation": expected_translation
                        })
                    else:
                        correct_phrases += 1

    accuracy = (correct_phrases / total_phrases) * 100 if total_phrases > 0 else 0

    # Save the mismatches
    with open(output_file, 'w', encoding='utf-8') as output_f:
        json.dump({
            "accuracy": f"{accuracy:.2f}%",
            "total_phrases": total_phrases,
            "correct_phrases": correct_phrases,
            "mismatches": mismatches
        }, output_f, ensure_ascii=False, indent=4)

    print(f"Evaluation completed. Results saved to {output_file}")

# Paths to the files
original_file = "chunks_output.json"  # Korean source
translated_files = [
    "chunks_google.json",
    "chunks_marian.json",
    "chunks_Mbart50.json",
    "chunks_Easy.json"
]

# Evaluate each translation file
for translated_file in translated_files:
    model_name = translated_file.split("_")[1].split(".")[0]
    output_file = f"evaluation_{model_name}.json"
    print(f"Evaluating model: {model_name}")
    evaluate_translation(original_file, translated_file, output_file)
