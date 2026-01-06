import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import Chapter, PracticeQuestion

chapter = Chapter.objects.filter(code='2.3.1').first()
if chapter:
    questions = PracticeQuestion.objects.filter(chapter=chapter).order_by('number')
    total = questions.count()
    with_exp = questions.exclude(explanation='').exclude(explanation__isnull=True).count()
    print(f'Chapter: {chapter.code} {chapter.title}')
    print(f'Questions with explanations: {with_exp} / {total}')
    print()
    for q in questions:
        exp_len = len(q.explanation) if q.explanation else 0
        status = '✓' if exp_len > 50 else '✗'
        print(f'{status} Q{q.number}: {exp_len} chars')
        if exp_len > 0:
            print(f'   Preview: {q.explanation[:100]}...')
else:
    print('Chapter not found')
