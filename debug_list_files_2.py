import os
import django
import sys
import google.generativeai as genai

# Setup Django Environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings


def list_files():
    api_key = settings.GEMINI_API_KEY
    genai.configure(api_key=api_key)

    with open("debug_files_list_2.txt", "w", encoding="utf-8") as f:
        f.write("--- Cloud Files ---\n")
        try:
            for file in genai.list_files():
                f.write(f"Name: {file.name}\n")
                f.write(f"Display Name: {file.display_name}\n")
                f.write(f"State: {file.state.name}\n")
                f.write("-" * 20 + "\n")
        except Exception as e:
            f.write(f"Error listing files: {e}\n")


if __name__ == "__main__":
    list_files()
