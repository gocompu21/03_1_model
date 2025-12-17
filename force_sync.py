from fileSearchStore import GeminiStoreManager
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print("Initializing Manager...")
manager = GeminiStoreManager(api_key=api_key)
print("Syncing stores...")
stores = manager.sync_all_stores()
print("Sync Result Keys:", list(stores.keys()))
print("수목병리학 files:", stores.get("수목병리학", "Not Found"))
