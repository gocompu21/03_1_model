import os
import django
import sys

# Django Setup
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from glossary.models import Term, Subject

def count_terms():
    try:
        subject = Subject.objects.get(name="수목생리학")
        count = Term.objects.filter(subjects=subject).count()
        print(f"수목생리학 과목에 등록된 용어 수: {count}")
    except Subject.DoesNotExist:
        print("수목생리학 과목이 존재하지 않습니다.")

if __name__ == "__main__":
    count_terms()
