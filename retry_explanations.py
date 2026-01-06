"""
Script to retry updating practice question explanations for Q4-Q10.
Target: Chapter 2.3.1 (세균의 분류)
"""
import os
import django
import time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from practice.models import Chapter, PracticeQuestion
from fileSearchStore import GeminiStoreManager

# Initialize
api_key = settings.GEMINI_API_KEY
manager = GeminiStoreManager(api_key=api_key)

# Find chapter
chapter = Chapter.objects.filter(code='2.3.1').first()
if not chapter:
    print('Chapter not found!')
    exit(1)

# Target questions Q4 to Q10
questions = PracticeQuestion.objects.filter(chapter=chapter, number__gte=4).order_by('number')
print(f'Retrying {questions.count()} questions (Q4-Q10)')

STORE_NAME = "수목병리학"
print(f'Using store: {STORE_NAME}')

for q in questions:
    print(f'\n{"="*50}')
    print(f'Processing Q{q.number}')
    
    query = f"""다음 나무의사 자격 시험 문제에 대한 상세한 해설을 기본서 내용에 근거하여 작성해주세요.

[문제]
{q.content}

[선지]
1. {q.choice1}
2. {q.choice2}
3. {q.choice3}
4. {q.choice4}
5. {q.choice5}

[정답]
{q.answer}번

[작성 가이드]
1. 정답인 이유를 기본서의 관련 내용을 인용하거나 풀어서 자세히 설명해주세요.
2. 오답 선지들이 왜 틀린지 각각 설명해주세요.
3. 문제와 관련된 '세균의 분류' 핵심 개념을 요약해주세요.
"""
    
    retries = 3
    for i in range(retries):
        print(f'Attempt {i+1}/{retries}...')
        try:
            response = manager.query_store(STORE_NAME, query)
            
            # Check length validity
            if response and len(response) > 300 and not response.startswith('Error') and not response.startswith('No valid'):
                q.explanation = response
                q.save()
                print(f'✓ Success! Saved {len(response)} chars')
                break
            else:
                print(f'✗ Output too short or invalid ({len(response) if response else 0} chars). Retrying...')
                print(f'Preview: {response[:100] if response else "None"}...')
                time.sleep(5) # Wait before retry
                
        except Exception as e:
            print(f'✗ Error: {e}')
            time.sleep(5)
    
    # Cooldown between questions
    print('Cooling down...')
    time.sleep(5)

print('\n=== Retry Complete ===')
