import os
import sys
import unicodedata
import json
import google.generativeai as genai
from django.conf import settings
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

genai.configure(api_key=settings.GEMINI_API_KEY)

target_store = "수목병리학"
print(f"Target Store: {target_store}")
norm_target = unicodedata.normalize("NFC", target_store)
print(f"Normalized Target: {ascii(norm_target)}")

# Simulate list_files
print("Listing files...")
cloud_files = genai.list_files()
active_files = []

for f in cloud_files:
    if f.state.name == "ACTIVE":
        dname = f.display_name
        norm_name = unicodedata.normalize("NFC", dname)
        print(f"Checking: {ascii(dname)} -> Norm: {ascii(norm_name)}")

        if norm_target in norm_name:
            print("  MATCH!")
            active_files.append(f.name)
        else:
            print("  NO MATCH")

print(f"Active Files Found: {active_files}")

# Simulate local_stores.json logic
store_file = "local_stores.json"
if os.path.exists(store_file):
    with open(store_file, "r") as f:
        data = json.load(f)
        print(f"Current JSON content for {target_store}: {data.get(target_store)}")
