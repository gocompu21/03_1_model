import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

print("Listing all files in Gemini Cloud...")
files = list(genai.list_files())
print(f"Total Files Found: {len(files)}")
print("-" * 60)
print(f"{'Display Name':<40} | {'Name':<20} | {'State':<10}")
print("-" * 60)
for f in files:
    print(f"{f.display_name[:37]:<40} | {f.name:<20} | {f.state.name:<10}")
print("-" * 60)
