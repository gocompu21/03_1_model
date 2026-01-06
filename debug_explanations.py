"""
Check and show current explanations for chapter 2.3.1
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import Chapter, PracticeQuestion

chapter = Chapter.objects.filter(code='2.3.1').first()
if chapter:
    questions = PracticeQuestion.objects.filter(chapter=chapter).order_by('number')
    
    for q in questions:
        print(f'=== Q{q.number} (ID: {q.id}) ===')
        print(f'Content: {q.content}')
        print(f'Answer: {q.answer}')
        print(f'Explanation length: {len(q.explanation) if q.explanation else 0}')
        print(f'Explanation: {repr(q.explanation)}')
        print()
