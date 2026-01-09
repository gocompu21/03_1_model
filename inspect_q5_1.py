import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from exam.models import Question

q = Question.objects.get(exam__round_number=5, number=1, subject__name='수목병리학')
print(f"ID: {q.id}")
print("Textbook Chat:")
print(q.textbook_chat)
print("-" * 20)
print("General Chat:")
print(q.general_chat)

with open('q5_1_detail.txt', 'w', encoding='utf-8') as f:
    f.write(f"Question ID: {q.id}\n")
    f.write("=== Textbook Chat ===\n")
    f.write(q.textbook_chat or "")
    f.write("\n\n=== General Chat ===\n")
    f.write(q.general_chat or "")
