import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import Chapter, PracticeQuestion

# Find chapter 2.3.2
chapter = Chapter.objects.filter(code='2.3.2').first()
if chapter:
    print(f'=== Chapter Info ===')
    print(f'Code: {chapter.code}')
    print(f'Title: {chapter.title}')
    print(f'Book: {chapter.book.name}')
    
    questions = PracticeQuestion.objects.filter(chapter=chapter).order_by('number')
    print(f'Total Questions: {questions.count()}')
    for q in questions[:10]:
        print(f'Q{q.number}: {q.content[:50]}...')
else:
    print('Chapter 2.3.2 not found')
