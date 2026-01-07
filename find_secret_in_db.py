
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import ChapterContent, PracticeQuestion

print("Searching ChapterContent...")
for cc in ChapterContent.objects.all():
    if cc.content and "AIza" in cc.content:
        print(f"Found in ChapterContent ID {cc.id}, Chapter {cc.chapter.code} {cc.chapter.title}")
        index = cc.content.find("AIza")
        print(f"Context: {cc.content[max(0, index-50):min(len(cc.content), index+50)]}")

print("Searching PracticeQuestion Explanations...")
for pq in PracticeQuestion.objects.all():
    if pq.explanation and "AIza" in pq.explanation:
        print(f"Found in PracticeQuestion ID {pq.id}, Chapter {pq.chapter.code}")
        index = pq.explanation.find("AIza")
        print(f"Context: {pq.explanation[max(0, index-50):min(len(pq.explanation), index+50)]}")
