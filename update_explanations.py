"""
Script to update practice question explanations by querying textbook file search.
Usage: python update_explanations.py <chapter_code>
Example: python update_explanations.py 2.4.1
"""
import os
import django
import time
import argparse
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from practice.models import Chapter, PracticeQuestion
from fileSearchStore import GeminiStoreManager

def update_explanations(chapter_code):
    # Initialize
    api_key = settings.GEMINI_API_KEY
    manager = GeminiStoreManager(api_key=api_key)

    # Find chapter
    chapter = Chapter.objects.filter(code=chapter_code).first()
    if not chapter:
        print(f'Error: Chapter with code "{chapter_code}" not found!')
        return

    print(f'=== Processing Chapter: {chapter.code} {chapter.title} ===')
    print(f'Book: {chapter.book.name}')
    
    # Use the correct store name based on the book subject/name
    # For now defaulting to checking the book subject or name
    # You might want to map this dynamically if needed
    store_name = chapter.book.subject if chapter.book.subject else chapter.book.name
    # Fallback/Override for known books if needed, e.g. "수목병리학"
    if "병리학" in chapter.book.name:
        store_name = "수목병리학"
    
    print(f'Using store: {store_name}')

    # Get questions
    questions = PracticeQuestion.objects.filter(chapter=chapter).order_by('number')
    print(f'Total questions: {questions.count()}')

    # Process each question
    for q in questions:
        print(f'\n{"="*50}')
        print(f'Q{q.number} (ID: {q.id})')
        print(f'Content: {q.content}')
        print(f'Answer: {q.answer}')
        
        # Check if explanation already exists (length check)
        if q.explanation and len(q.explanation.strip()) > 30:
            print(f'✓ Skipping: Already has explanation ({len(q.explanation)} chars)')
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
            response = manager.query_store(store_name, query)
            print(f'Response length: {len(response) if response else 0}')
            
            if response and len(response) > 100 and not response.startswith('Error') and not response.startswith('No valid'):
                # Update explanation
                q.explanation = response
                q.save()
                print(f'✓ Explanation saved')
                # Rate limiting
                time.sleep(3)
            else:
                print(f'✗ Response invalid or too short')
            
        except Exception as e:
            print(f'✗ Error: {e}')
            time.sleep(5)

    print('\n=== Done! ===')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Update explanations for a specific chapter.')
    parser.add_argument('code', type=str, help='Chapter code (e.g., 2.4.1)')
    
    args = parser.parse_args()
    update_explanations(args.code)
