import os
import sys
import google.generativeai as genai
import django

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

try:
    django.setup()
    from django.conf import settings

    api_key = getattr(settings, "GEMINI_API_KEY", "")
except Exception as e:
    print(f"Django setup failed: {e}")
    sys.exit(1)

if not api_key:
    print("API Key not found in settings.")
    sys.exit(1)

genai.configure(api_key=api_key)

models_to_test = [
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.0-flash-exp",
    "gemini-1.5-flash",
]

print("--- Testing Models ---")
for model_name in models_to_test:
    print(f"Testing {model_name}...")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello")
        print(f"SUCCESS: {model_name}")
    except Exception as e:
        print(f"FAILED: {model_name}")
        # print(f"Error details: {e}") # Uncomment for verbose error
