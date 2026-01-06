import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import Chapter, PracticeQuestion
import re

chapter = Chapter.objects.filter(code='2.3.1').first()
if chapter:
    questions = PracticeQuestion.objects.filter(chapter=chapter)
    print(f'Checking {questions.count()} questions for asterisks')
    
    for q in questions:
        if q.explanation and '*' in q.explanation:
            print(f'Q{q.number}: Found asterisk')
            print(q.explanation[:100])
            # Check specific pattern
            if re.search(r'\*\s*[①-⑮]', q.explanation):
                print('  -> Matches pattern * ①')
