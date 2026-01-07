
import os
import google.genai as genai
from django.conf import settings
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

client = genai.Client(api_key=settings.GEMINI_API_KEY)

print("Listing models...")
try:
    for model in client.models.list(config={}):
        name = model.name
        # Check supported generation methods or modalities?
        # The SDK object might have 'supported_generation_methods'
        methods = getattr(model, 'supported_generation_methods', [])
        print(f"Model: {name}, Methods: {methods}")
except Exception as e:
    print(f"Error listing models: {e}")
