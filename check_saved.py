import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import PracticeQuestion, Chapter

chapter = Chapter.objects.get(id=51)
print(f"📚 Chapter: {chapter.code} {chapter.title}")
print("=" * 60)

qs = PracticeQuestion.objects.filter(chapter_id=51).order_by('number')
print(f"총 {qs.count()}개 문제\n")

for q in qs:
    content_preview = q.content[:45].replace('\n', ' ')
    print(f"#{q.number:2d} | 정답:{q.answer} | {content_preview}...")
