import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import Chapter, PracticeQuestion
from django.db.models.functions import Length

chapter = Chapter.objects.filter(code='1.3.3.8').first()
if chapter:
    qs = PracticeQuestion.objects.filter(chapter=chapter).annotate(l=Length('explanation'))
    print(f"Chapter: {chapter.code} {chapter.title}")
    for q in qs:
        print(f"Q{q.number}: Length={q.l}")
else:
    print("Chapter 2.3.1 not found.")
