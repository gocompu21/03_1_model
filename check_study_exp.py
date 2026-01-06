import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from exam.models import Exam, Question

exam = Exam.objects.filter(round_number=5).first()
if exam:
    q = Question.objects.filter(exam=exam).first()
    if q:
        print(f'Exam 5 Q{q.number} Content')
        # Check textbook_chat or general_chat
        exp = q.textbook_chat if q.textbook_chat else q.general_chat
        print(f'Explanation Start: {exp[:200] if exp else "None"}')
        if exp and '*' in exp:
            print('Contains asterisk')
        else:
            print('No asterisk')
