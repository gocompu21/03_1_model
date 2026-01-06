"""
Script to update practice question explanations for Chapter 2.3.2 using Standard Prompt
"""
import os
import django
import time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from practice.models import Chapter, PracticeQuestion
from fileSearchStore import GeminiStoreManager, SYSTEM_INSTRUCTION

# Initialize
api_key = settings.GEMINI_API_KEY
manager = GeminiStoreManager(api_key=api_key)

# Find chapter 2.3.2
chapter = Chapter.objects.filter(code='2.3.2').first()
if not chapter:
    print('Chapter 2.3.2 not found!')
    exit(1)

# Get questions
questions = PracticeQuestion.objects.filter(chapter=chapter).order_by('number')
print(f'Processing {questions.count()} questions for Chapter 2.3.2 ({chapter.title})')

STORE_NAME = "수목병리학"
print(f'Using store: {STORE_NAME}')

for q in questions:
    print(f'\n{"="*50}')
    print(f'Processing Q{q.number}')
    
    # EXACT Prompt format from app_getTextbook.py
    prompt_content = (
        f"{q.number}. {q.content}\n"
        f"① {q.choice1}\n"
        f"② {q.choice2}\n"
        f"③ {q.choice3}\n"
        f"④ {q.choice4}\n"
        f"⑤ {q.choice5}"
    )

    prompt = f"{SYSTEM_INSTRUCTION}\n\n[문제]\n{prompt_content}"
    
    # Retry logic
    max_retries = 3
    retry_delay = 10
    
    for attempt in range(max_retries):
        try:
            print(f'Attempt {attempt+1}/{max_retries}...')
            response = manager.query_store(STORE_NAME, prompt)
            
            if response and len(response) > 200 and not response.startswith('Error'):
                q.explanation = response
                q.save()
                print(f'✓ Success! Saved {len(response)} chars')
                break
            else:
                print(f'✗ Short or error response. Retrying...')
                time.sleep(retry_delay)
                
        except Exception as e:
            print(f'✗ Error: {e}')
            time.sleep(retry_delay)
    
    # Cooldown
    print('Cooling down...')
    time.sleep(5)

print('\n=== Done ===')
