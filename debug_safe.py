import os
import sys
import django
from django.conf import settings

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import google.generativeai as genai

# Configure
api_key = settings.GEMINI_API_KEY
genai.configure(api_key=api_key)

print("--- CLOUD FILES (ESCAPED) ---")
for f in genai.list_files():
    # Print as ascii repr
    print(
        f"ID: {f.name} | DisplayName: {ascii(f.display_name)} | State: {f.state.name}"
    )
