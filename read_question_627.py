import os
import django
import sys

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from exam.models import Question

try:
    q = Question.objects.get(id=627)
    with open('question_627_chat.txt', 'w', encoding='utf-8') as f:
        f.write(q.textbook_chat)
    print("Saved to question_627_chat.txt")
except Question.DoesNotExist:
    print("Question 627 not found")
