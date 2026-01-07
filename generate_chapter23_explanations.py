"""
Script to generate textbook explanations for practice questions under chapter 2.3.
Uses GeminiStoreManager to query the 수목병리학 store.
"""
import os
import time
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from practice.models import Chapter, PracticeQuestion
from fileSearchStore import GeminiStoreManager, SYSTEM_INSTRUCTION

# Start from a specific question ID (to resume after rate limit)
START_FROM_ID = 34  # Change this to resume from where it stopped

def generate_explanations():
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set")
        return
    
    manager = GeminiStoreManager(api_key=api_key)
    
    # Get all chapters starting with 2.3 for book_id=1 (수목병리학)
    chapters = Chapter.objects.filter(code__startswith='2.3', book_id=1)
    print(f"Found {chapters.count()} chapters under 2.3")
    
    # Get all questions for these chapters, starting from START_FROM_ID
    questions = PracticeQuestion.objects.filter(
        chapter__in=chapters, 
        id__gte=START_FROM_ID
    ).order_by('id')
    print(f"Found {questions.count()} questions to process (starting from ID {START_FROM_ID})")
    
    # Process each question
    for i, q in enumerate(questions):
        print(f"\n[{i+1}/{questions.count()}] Question ID {q.id} (Chapter {q.chapter.code} #{q.number})")
        
        # Overwrite mode: always generate new explanation
        
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
        
        # Query store with retry logic
        print("  Querying 수목병리학 store...")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response_text = manager.query_store("수목병리학", prompt)
                
                if "Error" in response_text or "not found" in response_text.lower():
                    print(f"  Error: {response_text[:100]}")
                    break
                
                # Update explanation
                q.explanation = response_text
                q.save()
                print(f"  Saved explanation ({len(response_text)} chars)")
                break
                
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "quota" in error_str.lower():
                    wait_time = 20 * (attempt + 1)  # 20s, 40s, 60s
                    print(f"  Rate limit hit, waiting {wait_time}s... (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    print(f"  Exception: {e}")
                    break
        
        # Longer delay between requests to avoid rate limit (10 seconds)
        time.sleep(10)
    
    print("\n\nDone!")

if __name__ == "__main__":
    generate_explanations()

