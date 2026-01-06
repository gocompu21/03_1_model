"""
Targeted update for Q6 and Q10 in Chapter 2.3.1
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

# Target questions Q6 and Q10
questions = PracticeQuestion.objects.filter(chapter=chapter, number__in=[6, 10]).order_by('number')
print(f'Processing {questions.count()} questions (Q6, Q10)')

STORE_NAME = "수목병리학"
print(f'Using store: {STORE_NAME}')

for q in questions:
    print(f'\n{"="*50}')
    print(f'Processing Q{q.number}')
    print(f'Content: {q.content}')
    
    # Simplified query
    query = f"""나무의사 시험 문제 풀이와 해설을 부탁합니다.

문제: {q.content}

보기:
1. {q.choice1}
2. {q.choice2}
3. {q.choice3}
4. {q.choice4}
5. {q.choice5}

정답: {q.answer}번

해설 요청:
이 문제가 묻는 핵심 개념과 정답이 되는 이유, 그리고 오답이 틀린 이유를 기본서 내용을 바탕으로 설명해주세요.
"""
    
    try:
        print('Querying...')
        response = manager.query_store(STORE_NAME, query)
        
        if response and len(response) > 200:
            q.explanation = response
            q.save()
            print(f'✓ Success! Saved {len(response)} chars')
        else:
            print(f'✗ Failed. Response length: {len(response) if response else 0}')
            if response:
                print(f'Preview: {response[:100]}...')
                
    except Exception as e:
        print(f'✗ Error: {e}')
    
    print('Cooling down for 10 seconds...')
    time.sleep(10)

print('\n=== Done ===')
