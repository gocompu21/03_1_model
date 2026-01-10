"""
Script to update practice question explanations by querying textbook file search.
Target: Chapter 2.4.1.1 (파이토플라즈마의 특성 및 진단) - ID: 209
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

# Find chapter 2.4.1.1
chapter = Chapter.objects.filter(id=209).first()
if not chapter:
    print('Chapter 209 not found!')
    exit(1)

print(f'=== Processing Chapter: {chapter.code} {chapter.title} ===')
print(f'Book: {chapter.book.name}')

# Get questions
questions = PracticeQuestion.objects.filter(chapter=chapter).order_by('number')
print(f'Total questions: {questions.count()}')

# Use the correct store name for 수목병리학
STORE_NAME = "수목병리학"
print(f'Using store: {STORE_NAME}')

# Process each question
for q in questions:
    print(f'\n{"="*50}')
    print(f'Q{q.number} (ID: {q.id})')
    print(f'Content: {q.content}')
    print(f'Answer: {q.answer}')
    
    # Check if explanation already exists (length check or keyword)
    if q.explanation and len(q.explanation) > 50:
        print('Skipping: Already has explanation')
        # Uncomment to force update
        # pass 
        continue

    # Build query prompt for explanation
    query = f"""다음 나무의사 시험 문제에 대해 기본서 내용을 바탕으로 상세한 해설을 작성해주세요.

[문제]
{q.content}

[선지]
① {q.choice1}
② {q.choice2}
③ {q.choice3}
④ {q.choice4}
⑤ {q.choice5}

[정답]
{q.answer}번

[요청사항]
1. 정답이 왜 맞는지 기본서 내용을 인용하여 설명해주세요.
2. 각 오답 선지가 왜 틀린지 간략히 설명해주세요.
3. 관련 핵심 개념을 정리해주세요.
"""
    
    print(f'Querying textbook...')
    try:
        response = manager.query_store(STORE_NAME, query)
        print(f'Response length: {len(response) if response else 0}')
        
        if response and len(response) > 100 and not response.startswith('Error') and not response.startswith('No valid'):
            # Update explanation
            q.explanation = response
            q.save()
            print(f'✓ Explanation saved')
        else:
            print(f'✗ Response invalid or too short')
        
        # Rate limiting
        time.sleep(3)
        
    except Exception as e:
        print(f'✗ Error: {e}')
        time.sleep(5)

print('\n=== Done! ===')
