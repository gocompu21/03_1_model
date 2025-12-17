import google.generativeai as genai
import os
import unicodedata
import sys
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

subject_mappings = {
    "수목병리학": ["수목병리학"],
}

print("Debug Sync Logic:")
for f in genai.list_files():
    raw_name = f.display_name
    norm_name = unicodedata.normalize("NFC", raw_name)

    # Check match
    matched = False
    for subject, keywords in subject_mappings.items():
        if any(k in norm_name for k in keywords):
            print(f"MATCH: '{raw_name}' -> {subject} (norm: '{norm_name}')")
            matched = True

    if not matched and "병리" in raw_name:  # Broad check to see if we missed it
        print(
            f"MISSED candidate: '{raw_name}' (norm: '{norm_name}') - Keywords: {first_keywords}"
        )

print("Done.")
