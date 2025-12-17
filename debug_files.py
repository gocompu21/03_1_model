import os
import sys
import django
from django.conf import settings

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import google.generativeai as genai

# Configure
api_key = settings.GEMINI_API_KEY
genai.configure(api_key=api_key)

file_ids = ["files/nwn9o897ylsa", "files/ui71j943xxhe", "files/hrmalbwgujo2"]

print("--- FILE INFO ---")
for fid in file_ids:
    try:
        f = genai.get_file(fid)
        print(f"ID: {fid} | Name: {f.display_name} | State: {f.state.name}")
    except Exception as e:
        print(f"ID: {fid} | Error: {e}")
