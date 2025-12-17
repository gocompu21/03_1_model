"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()

# --- Auto-Sync Logic (Added) ---
try:
    from fileSearchStore import GeminiStoreManager
    import os
    from dotenv import load_dotenv

    # Ensure env is loaded for API KEY
    project_folder = os.path.expanduser(
        "~/myproject/03_1_model"
    )  # Adjust for server user path if needed or rely on cwd
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        print(" [WSGI] Starting Auto-Sync for Gemini Stores...")
        manager = GeminiStoreManager(api_key=api_key)
        manager.sync_all_stores()
        print(" [WSGI] Auto-Sync Completed.")
    else:
        print(" [WSGI] Skipped Auto-Sync (No API Key found).")
except Exception as e:
    print(f" [WSGI] Auto-Sync Failed: {e}")
# -------------------------------
