"""
Script to update practice question explanations by querying textbook file search.
Target: Chapter 2.3.1 (세균의 분류)
"""
import os
import django
import time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from django.db.models import Q
from django.db.models.functions import Length
from practice.models import Chapter, PracticeQuestion
from fileSearchStore import GeminiStoreManager

# Initialize
api_key = settings.GEMINI_API_KEY
manager = GeminiStoreManager(api_key=api_key)

# Get questions with short or empty explanations (<= 200 chars) across ALL chapters
questions = PracticeQuestion.objects.select_related('chapter__book').annotate(
    exp_len=Length('explanation')
).filter(
    Q(explanation__isnull=True) | Q(explanation='') | Q(exp_len__lte=200)
).order_by('chapter', 'number')

total_count = questions.count()
print(f'Total target questions found: {total_count}')

# Process each question
for i, q in enumerate(questions):
    print(f'\n{"="*50}')
    print(f'[{i+1}/{total_count}] Chapter: {q.chapter.code} ({q.chapter.book.subject})')
    print(f'Q{q.number} (ID: {q.id})')
    print(f'Content: {q.content}')
    
    # Correct Store Name from subject
    STORE_NAME = q.chapter.book.subject
    print(f'Using store: {STORE_NAME}')
    
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
        
        if response and len(response) > 100 and not response.startswith('Error') and not response.startswith('No valid') and not response.startswith('Store not found'):
            # Update explanation
            q.explanation = response
            q.save()
            print(f'✓ Explanation saved')
        else:
            print(f'✗ Response invalid or too short: "{response}"')
        
        # Rate limiting (60 seconds per user request)
        print("Waiting 60 seconds...")
        time.sleep(60)
        
    except Exception as e:
        print(f'✗ Error: {e}')
        time.sleep(10)

print('\n=== All target questions processed! ===')
