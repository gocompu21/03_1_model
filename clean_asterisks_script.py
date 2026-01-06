"""
Script to clean up asterisks from explanations in chapters 2.3.1 and 2.3.2
Removes '* ①' pattern and similar variations.
"""
import os
import django
import re
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import Chapter, PracticeQuestion

def clean_asterisks(text):
    if not text:
        return text
    
    # Remove '* ' before circled numbers
    # Pattern: asterisk, optional whitespace, optional bold, circled number
    # Example: * ① -> ①, * **① -> **①
    
    # Simple replacement for * ①
    text = re.sub(r'\*\s*([①-⑮])', r'\1', text)
    
    # Replacement for * **①
    text = re.sub(r'\*\s*(\*\*[①-⑮])', r'\1', text)
    
    return text

target_chapters = ['2.3.1', '2.3.2']
count = 0

for code in target_chapters:
    chapter = Chapter.objects.filter(code=code).first()
    if not chapter:
        continue
        
    questions = PracticeQuestion.objects.filter(chapter=chapter)
    print(f'Cleaning {chapter.code} ({questions.count()} questions)')
    
    for q in questions:
        if not q.explanation:
            continue
            
        original = q.explanation
        cleaned = clean_asterisks(original)
        
        if original != cleaned:
            q.explanation = cleaned
            q.save()
            print(f'Q{q.number}: Cleaned asterisks')
            count += 1

print(f'Total {count} explanations cleaned.')
