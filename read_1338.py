import os
import sys
import django

sys.path.append(r'c:\Users\gocom\Documents\Antigravity\Django_BaseCamp\03_1_model')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import ChapterContent

try:
    content_obj = ChapterContent.objects.get(chapter_id=406)
    with open('final_output.txt', 'w', encoding='utf-8') as f:
        f.write(content_obj.content)
    print("Content saved to final_output.txt")
except Exception as e:
    print(f"Error reading content: {e}")
