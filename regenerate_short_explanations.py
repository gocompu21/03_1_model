"""
Script to regenerate explanations for questions with short explanations (<=200 chars).
"""
import os
import time
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from django.db.models.functions import Length
from practice.models import Chapter, PracticeQuestion
from fileSearchStore import GeminiStoreManager, SYSTEM_INSTRUCTION

def regenerate_short_explanations():
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set")
        return
    
    manager = GeminiStoreManager(api_key=api_key)
    
    # Get chapters under 2.3
    chapters = Chapter.objects.filter(code__startswith='2.3', book_id=1)
    
    # Get questions with short explanations
    questions = PracticeQuestion.objects.filter(
        chapter__in=chapters
    ).annotate(
        exp_len=Length('explanation')
    ).filter(
        exp_len__lte=200
    ).order_by('id')
    
    print(f"Found {questions.count()} questions with explanation <= 200 chars")
    
    for i, q in enumerate(questions):
        print(f"\n[{i+1}/{questions.count()}] Question ID {q.id} (Chapter {q.chapter.code} #{q.number}, {q.exp_len} chars)")
        
        # Build prompt
        choices = [q.choice1 or "", q.choice2 or "", q.choice3 or "", q.choice4 or "", q.choice5 or ""]
        prompt_content = (
            f"{q.content}\n"
            f"① {choices[0]}\n"
            f"② {choices[1]}\n"
            f"③ {choices[2]}\n"
            f"④ {choices[3]}\n"
            f"⑤ {choices[4]}"
        )
        prompt = f"{SYSTEM_INSTRUCTION}\n\n[문제]\n{prompt_content}"
        
        # Query store with retry
        print("  Querying 수목병리학 store...")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response_text = manager.query_store("수목병리학", prompt)
                
                if "Error" in response_text or "not found" in response_text.lower():
                    print(f"  Error: {response_text[:100]}")
                    break
                
                q.explanation = response_text
                q.save()
                print(f"  Saved ({len(response_text)} chars)")
                break
                
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    wait_time = 20 * (attempt + 1)
                    print(f"  Rate limit, waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"  Exception: {e}")
                    break
        
        time.sleep(30)  # 30 seconds between calls
    
    print("\n\nDone!")

if __name__ == "__main__":
    regenerate_short_explanations()
