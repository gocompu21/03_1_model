import os
import sys
import google.generativeai as genai
from dotenv import load_dotenv

# Try loading .env directly
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    # If not in env, try looking for the file manually if needed, or check django settings?
    # Let's try to assume it is in the env context of the shell or .env file is present.
    print("API Key not found in environment.")
else:
    genai.configure(api_key=api_key)
    print("Checking files...")
    files = list(genai.list_files())
    if not files:
        print("No files found.")
    else:
        for f in files:
            print(
                f"Name: {f.name} | Display Name: {f.display_name} | State: {f.state.name}"
            )
