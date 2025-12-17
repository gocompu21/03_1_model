import google.generativeai as genai
import os
import sys

# Setup Django Environment for settings
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()
from django.conf import settings


def list_models():
    genai.configure(api_key=settings.GEMINI_API_KEY)
    with open("debug_models_out.txt", "w", encoding="utf-8") as f:
        print("Available Models:", file=f)
        try:
            for m in genai.list_models():
                if "generateContent" in m.supported_generation_methods:
                    print(m.name, file=f)
        except Exception as e:
            print(f"Error: {e}", file=f)


if __name__ == "__main__":
    list_models()
