import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from exam.models import Question, Exam

exam = Exam.objects.get(round_number=5)
q = Question.objects.filter(exam=exam, number=1).first()

print(f'Question ID: {q.id}')
print(f'Question number: {q.number}')
print(f'Narration exists: {bool(q.narration)}')
print(f'Narration length: {len(q.narration) if q.narration else 0}')
print(f'\nFirst 300 chars of narration:')
print(q.narration[:300] if q.narration else 'None')
