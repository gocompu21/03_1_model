"""
Script to restore asterisks in explanations for chapters 2.3.1 and 2.3.2
Reverse operation: ① -> * ①
"""
import os
import django
import re
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import Chapter, PracticeQuestion

def restore_asterisks(text):
    if not text:
        return text
    
    # Add '* ' before circled numbers if not present
    # Pattern: Not asterisk/whitespace, then circled number
    # We want to replace "①" with "* ①", but only at start of line or after newline
    
    # Using simple replacement for now, assuming standard format
    # Be careful not to double add asterisk if it already exists (though we cleaned them)
    
    # Replace "①" with "* ①"
    # Use negative lookbehind to avoid adding if already there (though regex support is limited)
    # Instead, we'll iterate lines
    
    lines = text.split('\n')
    new_lines = []
    
    for line in lines:
        stripped = line.strip()
        # Check if line starts with circled number (optionally bolded)
        # e.g. "①...", "**①...**", etc.
        if re.match(r'^(\*\*)?[①-⑮]', stripped):
            # If line doesn't start with '*', add '* '
            if not stripped.startswith('*'):
                line = '* ' + line.lstrip()
        
        new_lines.append(line)
    
    return '\n'.join(new_lines)

target_chapters = ['2.3.1', '2.3.2']
count = 0

for code in target_chapters:
    chapter = Chapter.objects.filter(code=code).first()
    if not chapter:
        continue
        
    questions = PracticeQuestion.objects.filter(chapter=chapter)
    print(f'Restoring {chapter.code} ({questions.count()} questions)')
    
    for q in questions:
        if not q.explanation:
            continue
            
        original = q.explanation
        restored = restore_asterisks(original)
        
        if original != restored:
            q.explanation = restored
            q.save()
            print(f'Q{q.number}: Restored asterisks')
            count += 1

print(f'Total {count} explanations restored.')
