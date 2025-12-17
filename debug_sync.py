import os
import sys
import django
from django.conf import settings

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from fileSearchStore import GeminiStoreManager

print("Initializing Manager...")
api_key = settings.GEMINI_API_KEY
print(f"API Key present: {bool(api_key)}")

manager = GeminiStoreManager(api_key=api_key)
print(f"Initial Stores: {manager.stores}")

print("Running sync_all_stores()...")
result = manager.sync_all_stores()
print(f"Sync Result: {result}")

store_name = "수목생리학"
if store_name in result and result[store_name]:
    print(f"SUCCESS: {store_name} has files: {result[store_name]}")
else:
    print(f"FAILURE: {store_name} is empty or missing.")
