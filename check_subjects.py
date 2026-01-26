import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import PracticeQuestion
from django.db.models.functions import Length
from django.db.models import Count, Q

targets = PracticeQuestion.objects.annotate(
    l=Length('explanation')
).filter(
    Q(explanation__isnull=True) | Q(explanation='') | Q(l__lte=200)
).values('chapter__book__subject').annotate(count=Count('id'))

print("--- Subject Distribution of Target Questions ---")
for t in targets:
    print(f"{t['chapter__book__subject']}: {t['count']} questions")
