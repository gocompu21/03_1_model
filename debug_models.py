import os
import sys
import google.generativeai as genai
from django.conf import settings
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

genai.configure(api_key=settings.GEMINI_API_KEY)

print("--- AVAILABLE MODELS ---")
for m in genai.list_models():
    print(
        f"Name: {m.name} | Supported Generation Methods: {m.supported_generation_methods}"
    )
