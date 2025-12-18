import os
import sys
import google.generativeai as genai
import django

# Setup Django to get settings (API Key)
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.conf import settings


def delete_pdf():
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        print("Error: No API Key found.")
        return

    genai.configure(api_key=api_key)

    file_id = "files/3h1n8rfbjo7g"
    print(f"Attempting to delete file: {file_id}")

    try:
        genai.delete_file(file_id)
        print(f"Successfully deleted {file_id}")
    except Exception as e:
        print(f"Error deleting file: {e}")


if __name__ == "__main__":
    delete_pdf()
