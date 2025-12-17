import google.generativeai as genai
import os
import sys
from dotenv import load_dotenv

# Force UTF-8 for stdout
sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

print("Listing all files in Gemini Cloud:")
found = False
for f in genai.list_files():
    # print(f"name: {f.name}, display_name: {f.display_name}, state: {f.state.name}")
    if "수목병리학" in f.display_name:
        print(
            f"FOUND: name={f.name}, display_name={f.display_name}, state={f.state.name}"
        )
        found = True
if not found:
    print("NOT FOUND: '수목병리학' not in any file display_name")
