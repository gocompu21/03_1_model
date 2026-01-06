import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import Chapter, PracticeQuestion

chapter = Chapter.objects.filter(code='2.3.2').first()
if chapter:
    q = PracticeQuestion.objects.filter(chapter=chapter, number=7).first()
    if q:
        print(f'=== Q{q.number} (ID: {q.id}) ===')
        print(f'Content: {q.content}')
        print(f'Explanation length: {len(q.explanation) if q.explanation else 0}')
        print(f'Explanation preview: {q.explanation[:200] if q.explanation else "(empty)"}')
    else:
        print('Q7 not found')
else:
    print('Chapter not found')
