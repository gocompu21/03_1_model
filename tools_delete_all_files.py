import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY not found in .env or environment.")
    exit(1)

genai.configure(api_key=api_key)

print("Fetching file list from Gemini Cloud...")
try:
    files = list(genai.list_files())
except Exception as e:
    print(f"Error listing files: {e}")
    exit(1)

if not files:
    print("No files found in the cloud store.")
    exit(0)

print(f"Found {len(files)} files. Starting deletion...")

for f in files:
    try:
        print(f"Deleting '{f.display_name}' ({f.name})...", end="")
        genai.delete_file(f.name)
        print(" Done.")
    except Exception as e:
        print(f" Failed: {e}")

print("-" * 30)
print("All deletion operations completed.")
