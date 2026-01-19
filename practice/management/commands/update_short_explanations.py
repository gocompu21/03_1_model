from django.core.management.base import BaseCommand
from django.db.models.functions import Length
from django.conf import settings
from practice.models import PracticeQuestion
from fileSearchStore import GeminiStoreManager, SYSTEM_INSTRUCTION
import time

class Command(BaseCommand):
    help = 'Regenerate explanations for practice questions with short explanations (<= 200 chars).'

    def handle(self, *args, **options):
        api_key = getattr(settings, 'GEMINI_API_KEY', '')
        if not api_key:
            self.stdout.write(self.style.ERROR("ERROR: GEMINI_API_KEY not set"))
            return

        manager = GeminiStoreManager(api_key=api_key)
        
        # Get questions with short explanations
        questions = PracticeQuestion.objects.annotate(
            exp_len=Length('explanation')
        ).filter(
            exp_len__lte=200
        ).order_by('id')
        
        total_count = questions.count()
        self.stdout.write(self.style.SUCCESS(f"Found {total_count} questions with explanation <= 200 chars"))
        
        if total_count == 0:
            return

        for i, q in enumerate(questions):
            self.stdout.write(f"\n[{i+1}/{total_count}] ID {q.id} ({q.chapter.code} #{q.number}, {q.exp_len} chars)")

            # Build prompt
            choices = [
                q.choice1 or "", q.choice2 or "", q.choice3 or "", 
                q.choice4 or "", q.choice5 or ""
            ]
            
            prompt_content = (
                f"{q.content}\n"
                f"① {choices[0]}\n"
                f"② {choices[1]}\n"
                f"③ {choices[2]}\n"
                f"④ {choices[3]}\n"
                f"⑤ {choices[4]}"
            )
            
            prompt = f"{SYSTEM_INSTRUCTION}\n\n[문제]\n{prompt_content}"
            
            # Query Logic with Fallback
            # Default to "수목관리학" then try fallbacks
            stores_to_try = ["수목관리학", "수목병리학", "수목생리학", "수목해충학", "산림토양학"]
            success = False
            
            for store_name in stores_to_try:
                self.stdout.write(f"  Querying {store_name}...")
                
                # Retry logic for each store (for rate limits)
                max_retries = 2
                for attempt in range(max_retries):
                    try:
                        response_text = manager.query_store(store_name, prompt)
                        
                        if "Error" in response_text or "not found" in response_text.lower():
                            # If not found in this store, break inner loop to try next store
                            # But if it's a specific error, maybe log it
                            break 
                        
                        # If we got a valid response
                        q.explanation = response_text
                        q.save()
                        self.stdout.write(self.style.SUCCESS(f"  Saved! ({len(response_text)} chars)"))
                        success = True
                        break 
                        
                    except Exception as e:
                        if "429" in str(e) or "quota" in str(e).lower():
                            wait_time = 30 * (attempt + 1)
                            self.stdout.write(self.style.WARNING(f"  Rate limit, waiting {wait_time}s..."))
                            time.sleep(wait_time)
                        else:
                            self.stdout.write(self.style.ERROR(f"  Exception: {e}"))
                            break
                
                if success:
                    break
            
            if not success:
                self.stdout.write(self.style.ERROR("  Failed to find explanation in any store."))

            # Sleep between questions to be nice to the API
            self.stdout.write(self.style.WARNING("  Waiting 60 seconds for API rate limit..."))
            time.sleep(60)

        self.stdout.write(self.style.SUCCESS("\nDone!"))
