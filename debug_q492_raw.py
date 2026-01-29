import os
import sys
import django

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from exam.models import Question

def dump_q492():
    try:
        q = Question.objects.get(id=492)
        print(f"--- Q{q.id} Content Repr ---")
        print(repr(q.content))
        print(f"--- Q{q.id} Textbook Chat Repr ---")
        print(repr(q.textbook_chat))
        print(f"--- Q{q.id} General Chat Repr ---")
        print(repr(q.general_chat))
    except Question.DoesNotExist:
        print("Q492 not found")

dump_q492()
