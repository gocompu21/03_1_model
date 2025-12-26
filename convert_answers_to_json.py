# Manual migration to convert answer field to JSONField
# This script handles the conversion in Python instead of relying on SQL

import os
import sys
import django
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from exam.models import Question

print("Converting answer field to JSON format...")

# Get all questions
questions = Question.objects.all()
total = questions.count()

print(f"Total questions to convert: {total}")

# Update each question
for i, q in enumerate(questions, 1):
    old_answer = q.answer
    
    # Convert integer to list
    if isinstance(old_answer, int):
        q.answer = [old_answer]
        q.save(update_fields=['answer'])
        if i % 100 == 0:
            print(f"  Processed {i}/{total}...")

print(f"✓ Conversion complete! {total} questions updated.")
print("\nSample conversions:")
for q in Question.objects.all()[:5]:
    print(f"  Q{q.id}: {q.answer}")
