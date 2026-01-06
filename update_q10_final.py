"""
Targeted update for Q10 only using Standard Prompt
"""
import os
import django
import time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import Chapter, PracticeQuestion
from fileSearchStore import GeminiStoreManager, SYSTEM_INSTRUCTION
from django.conf import settings

# Initialize
api_key = settings.GEMINI_API_KEY
manager = GeminiStoreManager(api_key=api_key)

# Find chapter
chapter = Chapter.objects.filter(code='2.3.1').first()
if not chapter:
    print('Chapter not found!')
    exit(1)

# Target Q10
q = PracticeQuestion.objects.filter(chapter=chapter, number=10).first()
if not q:
    print('Q10 not found')
    exit(1)

print(f'Processing Q10 (ID: {q.id})')
print(f'Current length: {len(q.explanation) if q.explanation else 0}')

STORE_NAME = "수목병리학"
print(f'Using store: {STORE_NAME}')

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

# Force Retry logic
max_retries = 5
retry_delay = 15

success = False
for attempt in range(max_retries):
    try:
        print(f'\nAttempt {attempt+1}/{max_retries}...')
        response = manager.query_store(STORE_NAME, prompt)
        
        if response and len(response) > 500 and not response.startswith('Error') and not response.startswith('No valid'):
            q.explanation = response
            q.save()
            print(f'✓ Success! Saved {len(response)} chars')
            success = True
            break
        else:
            print(f'✗ Failed or short response ({len(response) if response else 0} chars).')
            if response:
                print(f'Preview: {response[:100]}...')
            time.sleep(retry_delay)
            
    except Exception as e:
        print(f'✗ Error: {e}')
        time.sleep(retry_delay)

if not success:
    print('Failed to update Q10 after all attempts.')
else:
    print('Q10 Updated Successfully.')
