import os
import django
import sys

# Setup Django Environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from fileSearchStore import GeminiStoreManager


def check_store():
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        print("Error: GEMINI_API_KEY not found in settings.")
        return

    manager = GeminiStoreManager(api_key=api_key)
    target_store = "수목병리학"

    print(f"--- Checking Status for Store: '{target_store}' ---")

    # Check local store cache
    if target_store in manager.stores:
        files = manager.stores[target_store]
        print(f"Local Store Status: Found. File count: {len(files)}")
        if files:
            print(f"Files in local store: {files}")
        else:
            print("Files in local store: Empty")
    else:
        print("Local Store Status: Not found in local_stores.json")

    # Force Sync
    print("\n--- Triggering Force Sync ---")
    manager.sync_all_stores()

    # Re-check after sync
    if target_store in manager.stores:
        files = manager.stores[target_store]
        print(f"Post-Sync Status: Found. File count: {len(files)}")
        if files:
            print(f"Files: {files}")
        else:
            print("Files: Empty")
    else:
        print("Post-Sync Status: Not found")

    # List all cloud files to see if anything matches loosely
    print("\n--- All Cloud Files ---")
    cloud_files = manager.list_all_files()
    if not cloud_files:
        print("No files found in Gemini Cloud.")
    else:
        found_match = False
        for f in cloud_files:
            if "수목병리학" in f["display_name"]:
                found_match = True

        if found_match:
            print("\nResult: Files matching '수목병리학' EXIST in Cloud.")
        else:
            print("\nResult: NO files matching '수목병리학' found in Cloud.")


if __name__ == "__main__":
    check_store()
