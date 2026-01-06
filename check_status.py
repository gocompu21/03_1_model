import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import Chapter, PracticeQuestion

chapter = Chapter.objects.filter(code='2.3.1').first()
if chapter:
    questions = PracticeQuestion.objects.filter(chapter=chapter).order_by('number')
    print(f'Checking {questions.count()} questions for Chapter 2.3.1')
    
    for q in questions:
        exp_len = len(q.explanation) if q.explanation else 0
        status = 'OK' if exp_len > 300 else 'SHORT' if exp_len > 0 else 'MISSING'
        print(f'Q{q.number}: {status} ({exp_len} chars)')
