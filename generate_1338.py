import os
import sys
import django

sys.path.append(r'c:\Users\gocom\Documents\Antigravity\Django_BaseCamp\03_1_model')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from django.contrib.auth.models import User
from practice.models import Chapter, ChapterContent
from fileSearchStore import GeminiStoreManager

def generate_content():
    try:
        # 1. Fetch Chapter
        chapter = Chapter.objects.get(id=406)
        print(f"Target Chapter: {chapter.code} {chapter.title}")
        
        # 2. Setup Gemini Manager
        api_key = settings.GEMINI_API_KEY
        manager = GeminiStoreManager(api_key=api_key)
        manager.sync_all_stores()
        
        # 3. Construct Prompt
        subject = chapter.book.subject
        prompt = f"""
{chapter.code} {chapter.title}에 대해 자세히 정리해 주는 데 존대말로 하지 말고 "~함"으로 해주고 서적 페이지를 언급하지 말 것. 레퍼런스도 넣지 말 것.
번호는 (1),(2),(3) 형식으로 볼드체와 머리기호 등을 적절하게 사용하여 개조식으로 작성할 것.
{subject} 과목의 맥락에서 설명해.
"""
        print("Sending prompt to Gemini...")
        
        # 4. Query Gemini
        # Using subject as store name to retrieve relevant context if available
        content = manager.query_store(subject, prompt)
        
        print("\n--- Generated Content ---\n")
        print(content)
        print("\n-------------------------\n")
        
        print("Content generated successfully.")
        
        # 5. Save to DB
        author = User.objects.filter(is_superuser=True).first()
        if not author:
            author = User.objects.first()
            
        obj, created = ChapterContent.objects.update_or_create(
            chapter=chapter,
            defaults={
                'content': content,
                'author': author
            }
        )
        
        action = "Created" if created else "Updated"
        print(f"[{action}] Content saved for Chapter {chapter.id} (Content ID: {obj.id})")
        
    except Chapter.DoesNotExist:
        print("Chapter 406 not found.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    generate_content()
