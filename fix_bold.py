"""
Script to fix bold formatting in explanations for chapters 2.3.1 and 2.3.2
Target: Change "* *①" or "* ①" to "* **①"
"""
import os
import django
import re
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import Chapter, PracticeQuestion

def fix_bold(text):
    if not text:
        return text
    
    lines = text.split('\n')
    new_lines = []
    
    for line in lines:
        stripped = line.strip()
        # Check if line looks like a choice explanation item
        # Matches: "* ①", "* *①", "* **①"
        
        # We want to force it to "* **①"
        
        # Regex to capture the circled number and the rest of the line
        # Start of line, asterisk, spaces, optional asterisks, spaces, (circled number ...)
        
        # Case 1: * *①... -> * **①...
        # Case 2: * ①... -> * **①...
        
        if re.match(r'^\*\s*\*?\s*[①-⑮]', stripped):
            # Replace the start with "* **"
            # Find where the circled number starts
            match = re.search(r'([①-⑮])', stripped)
            if match:
                start_index = match.start()
                # Keep everything from the circled number onwards
                content = stripped[start_index:]
                line = '* **' + content
        
        new_lines.append(line)
    
    return '\n'.join(new_lines)

target_chapters = ['2.3.1', '2.3.2']
count = 0

for code in target_chapters:
    chapter = Chapter.objects.filter(code=code).first()
    if not chapter:
        continue
        
    questions = PracticeQuestion.objects.filter(chapter=chapter)
    print(f'Fixing bold in {chapter.code} ({questions.count()} questions)')
    
    for q in questions:
        if not q.explanation:
            continue
            
        original = q.explanation
        fixed = fix_bold(original)
        
        if original != fixed:
            q.explanation = fixed
            q.save()
            print(f'Q{q.number}: Fixed bold')
            count += 1

print(f'Total {count} explanations fixed.')
