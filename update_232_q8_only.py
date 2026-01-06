"""
Targeted update for Chapter 2.3.2 Q8 only
"""
import os
import django
import time
import re
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import Chapter, PracticeQuestion
from fileSearchStore import GeminiStoreManager, SYSTEM_INSTRUCTION
from django.conf import settings

# Initialize
api_key = settings.GEMINI_API_KEY
manager = GeminiStoreManager(api_key=api_key)

# Find chapter
chapter = Chapter.objects.filter(code='2.3.2').first()
if not chapter:
    print('Chapter not found!')
    exit(1)

# Target Q8
q = PracticeQuestion.objects.filter(chapter=chapter, number=8).first()
if not q:
    print('Q8 not found')
    exit(1)

print(f'Processing Q8 (ID: {q.id})')
print(f'Current length: {len(q.explanation) if q.explanation else 0}')

STORE_NAME = "수목병리학"

# EXACT Prompt format
prompt_content = (
    f"{q.number}. {q.content}\n"
    f"① {q.choice1}\n"
    f"② {q.choice2}\n"
    f"③ {q.choice3}\n"
    f"④ {q.choice4}\n"
    f"⑤ {q.choice5}"
)

prompt = f"{SYSTEM_INSTRUCTION}\n\n[문제]\n{prompt_content}"

# Helper to fix bold (Italic -> Bold)
def fix_bold(text):
    if not text:
        return text
    lines = text.split('\n')
    new_lines = []
    for line in lines:
        stripped = line.strip()
        # Matches: "* *①", "* ①" (at start of line)
        if re.match(r'^\*\s*\*?\s*[①-⑮]', stripped):
            match = re.search(r'([①-⑮])', stripped)
            if match:
                content = stripped[match.start():]
                line = '* **' + content
        new_lines.append(line)
    return '\n'.join(new_lines)

# Force Retry logic
max_retries = 5
retry_delay = 15

success = False
for attempt in range(max_retries):
    try:
        print(f'\nAttempt {attempt+1}/{max_retries}...')
        response = manager.query_store(STORE_NAME, prompt)
        
        if response and len(response) > 500 and not response.startswith('Error'):
            # Apply formatting fixes immediately
            fixed_response = fix_bold(response)
            
            q.explanation = fixed_response
            q.save()
            print(f'✓ Success! Saved {len(fixed_response)} chars')
            success = True
            break
        else:
            print(f'✗ Failed or short response ({len(response) if response else 0} chars).')
            time.sleep(retry_delay)
            
    except Exception as e:
        print(f'✗ Error: {e}')
        time.sleep(retry_delay)

if not success:
    print('Failed to update Q8 after all attempts.')
else:
    print('Q8 Updated Successfully.')
