
import os
import sys
import django
import unicodedata

# Django setup
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from fileSearchStore import GeminiStoreManager

def debug_gemini():
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in settings.")
        return

    manager = GeminiStoreManager(api_key=api_key)
    print(f"GeminiStoreManager initialized.")

    print("\n--- Cloud Files ---")
    cloud_files = manager.list_all_files()
    if not cloud_files:
        print("No files found in cloud.")
    else:
        for f in cloud_files:
            norm_name = unicodedata.normalize("NFC", f["display_name"])
            print(f"- {norm_name} ({f['name']}) [State: {f['state']}]")

    print("\n--- Store Mappings (Proposed) ---")
    # Simulate sync_all_stores logic
    subject_mappings = {
        "수목생리학": ["수목생리학"],
        "수목병리학": ["수목병리학"],
        "수목해충학": ["수목해충학"],
        "산림토양학": ["산림토양학", "토양학"],
        "수목관리학": ["수목관리학", "조경수", "식재관리", "농약학"],
    }

    for subject, keywords in subject_mappings.items():
        matched = []
        for f in cloud_files:
            if f["state"] == "ACTIVE":
                norm_name = unicodedata.normalize("NFC", f["display_name"])
                if any(k in norm_name for k in keywords):
                    matched.append(norm_name)
        print(f"Store '{subject}': {matched}")

    print("\n--- Current Local Stores ---")
    print(manager.stores)

if __name__ == "__main__":
    debug_gemini()
