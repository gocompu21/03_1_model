from dotenv import load_dotenv

load_dotenv()

import os
import google.generativeai as genai

api_key = os.getenv("GEMINI_API_KEY")
print(f"Using API Key: {api_key[:10]}...{api_key[-5:]}")

genai.configure(api_key=api_key)

print("\n=== Listing files from Gemini cloud ===")
files = list(genai.list_files())
print(f"Found {len(files)} files:\n")
for f in files:
    print(f"  [{f.state.name}] {f.display_name}")
    print(f"       -> {f.name}")

# Now sync to local stores
print("\n=== Syncing to local stores ===")
from fileSearchStore import GeminiStoreManager

m = GeminiStoreManager(api_key=api_key)
m.sync_all_stores()

print("\n=== Stores after sync ===")
for store, files in m.stores.items():
    print(f"{store}: {len(files)} files")
    for fn in files:
        print(f"  - {fn}")
