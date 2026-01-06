import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import Chapter, PracticeQuestion
import re

target_chapters = ['2.3.1', '2.3.2']

for code in target_chapters:
    chapter = Chapter.objects.filter(code=code).first()
    if chapter:
        print(f'=== Chapter {code} ===')
        questions = PracticeQuestion.objects.filter(chapter=chapter).order_by('number')
        for q in questions[:3]: # Check first 3 questions
            print(f'[Q{q.number}]')
            # Print lines starting with *
            if q.explanation:
                for line in q.explanation.split('\n'):
                    if line.strip().startswith('*'):
                        print(line.strip()[:100])
