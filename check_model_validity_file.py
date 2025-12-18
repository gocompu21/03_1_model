import os
import sys
import google.generativeai as genai
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.conf import settings

api_key = getattr(settings, "GEMINI_API_KEY", "")
genai.configure(api_key=api_key)

models_to_test = [
    "gemini-2.0-flash-exp",
    "gemini-2.0-flash",
    "gemini-1.5-pro",
    "gemini-1.5-pro-002",
    "gemini-1.5-flash-8b",
    "gemini-2.5-flash",
    "gemini-1.5-pro-latest",
]

with open("model_check_results.txt", "w") as f:
    for model_name in models_to_test:
        f.write(f"Testing {model_name}...\n")
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content("Hello")
            f.write(f"SUCCESS: {model_name}\n")
        except Exception as e:
            f.write(f"FAILED: {model_name} - {e}\n")
