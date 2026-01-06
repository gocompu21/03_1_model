import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import Chapter, PracticeQuestion

chapter = Chapter.objects.filter(code='2.3.1').first()
if chapter:
    q = PracticeQuestion.objects.filter(chapter=chapter).first()
    print(f'=== Q{q.number} Content ===')
    print(q.explanation[:500])
