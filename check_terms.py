import os
import sys
import django

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from glossary.models import Term

def check_short_terms():
    terms = Term.objects.filter(word__in=['c', 'C', 'cmol', 'kg', 'meq', '30'])
    print(f"Found {terms.count()} potential confusing terms.")
    for t in terms:
        print(f"Term: '{t.word}' (ID: {t.id})")

check_short_terms()
