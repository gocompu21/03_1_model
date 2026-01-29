import os
import sys
import django

# Django setup
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from glossary.models import Term

def check_term():
    try:
        term = Term.objects.get(id=5521)
        print(f"Term ID: {term.id}")
        print(f"Word: '{term.word}'")
        print(f"Word (repr): {repr(term.word)}")
    except Term.DoesNotExist:
        print("Term 5521 not found")

if __name__ == "__main__":
    check_term()
