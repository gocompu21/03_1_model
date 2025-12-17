import os
import django
import sys

# Setup Django Environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from fileSearchStore import GeminiStoreManager


def list_cloud_files():
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        print("Error: GEMINI_API_KEY not found in settings.")
        return

    manager = GeminiStoreManager(api_key=api_key)
    print("--- Listing Cloud Files ---")
    files = manager.list_all_files()
    if not files:
        print("No files found in Gemini Cloud.")
    else:
        for f in files:
            print(
                f"Name: {f['name']}, Display Name: {f['display_name']}, State: {f['state']}"
            )


if __name__ == "__main__":
    list_cloud_files()
