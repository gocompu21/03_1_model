import os
import django
import sys

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from glossary.models import Term

try:
    term = Term.objects.get(id=961)
    with open('term_961_content.txt', 'w', encoding='utf-8') as f:
        f.write(f"ID: {term.id}, Word: {term.word}\n")
        f.write("-" * 20 + "\n")
        f.write(term.content)
    print("Saved to term_961_content.txt")
except Term.DoesNotExist:
    print("Term 961 not found")
