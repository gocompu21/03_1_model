import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from exam.models import Question

q = Question.objects.get(exam__round_number=10, number=60)
with open('temp_amylase_check.txt', 'w', encoding='utf-8') as f:
    f.write(f"Content: {q.content}\n")
    f.write(f"General Chat: {q.general_chat}\n")
    f.write(f"Textbook Chat: {q.textbook_chat}\n")
