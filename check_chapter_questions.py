import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import Chapter, PracticeQuestion

# Find chapter 2.3.1
chapter = Chapter.objects.filter(code='2.3.1').first()
if chapter:
    print(f'=== Chapter Info ===')
    print(f'ID: {chapter.id}')
    print(f'Code: {chapter.code}')
    print(f'Title: {chapter.title}')
    print(f'Book: {chapter.book.name}')
    print()
    
    questions = PracticeQuestion.objects.filter(chapter=chapter).order_by('number')
    print(f'=== Questions ({questions.count()}) ===')
    
    for q in questions:
        print(f'\n[Q{q.number}] ID={q.id}')
        print(f'Content: {q.content}')
        print(f'1) {q.choice1}')
        print(f'2) {q.choice2}')
        print(f'3) {q.choice3}')
        print(f'4) {q.choice4}')
        print(f'5) {q.choice5}')
        print(f'Answer: {q.answer}')
        print(f'Has Explanation: {"Yes" if q.explanation else "No"}')
else:
    print('Chapter 2.3.1 not found')
    # List available chapters
    print('\nAvailable chapters:')
    for c in Chapter.objects.all()[:20]:
        print(f'  {c.code}: {c.title}')
