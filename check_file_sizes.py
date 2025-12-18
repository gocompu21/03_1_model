import os
import django
import sys
import google.generativeai as genai

# Setup Django Environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from fileSearchStore import GeminiStoreManager


def check_sizes():
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        print("Error: GEMINI_API_KEY not found.")
        return

    genai.configure(api_key=api_key)
    manager = GeminiStoreManager(api_key=api_key)

    # Assuming '수목병리학' is the target based on previous logs (files were listed in debug output)
    # In the logs, we saw files/3h1n8rfbjo7g (PDF) and files/7lonnuz21kr8 (txt)
    # Let's check THOSE specific files if possible, or just list the store.

    file_ids = ["files/3h1n8rfbjo7g", "files/7lonnuz21kr8"]

    with open("file_sizes.log", "w", encoding="utf-8") as log_file:
        log_file.write("--- Checking Sizes for Known Files ---\n")
        print("Checking sizes... check file_sizes.log")
        for fid in file_ids:
            try:
                f = genai.get_file(fid)
                log_file.write("-" * 30 + "\n")
                log_file.write(f"File ID: {f.name}\n")
                log_file.write(f"  Display Name: {f.display_name}\n")
                log_file.write(f"  MIME Type: {f.mime_type}\n")
                log_file.write(f"  Size (Bytes): {f.size_bytes}\n")
                log_file.write(f"  Size (MB): {f.size_bytes / (1024*1024):.2f} MB\n")
                log_file.write(f"  State: {f.state.name}\n")
                log_file.write("-" * 30 + "\n")
            except Exception as e:
                log_file.write(f"Error checking {fid}: {e}\n")


if __name__ == "__main__":
    check_sizes()
