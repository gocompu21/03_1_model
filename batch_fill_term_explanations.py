
import os
import sys
import django
import time

# Django setup
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from glossary.models import Term
from fileSearchStore import GeminiStoreManager

def main():
    print("=== 용어 설명 일괄 채우기 (Gemini API) ===")
    
    # 1. API Manager Init
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in settings.")
        return

    manager = GeminiStoreManager(api_key=api_key)
    print("✅ GeminiStoreManager initialized.")
    
    # Sync stores once
    print("🔄 Syncing stores...")
    manager.sync_all_stores()
    print("✅ Sync complete.")

    # 2. Get target terms (content empty)
    terms = Term.objects.filter(content__exact='').exclude(subjects=None) # Only terms with subjects? Or all?
    # Actually, let's include all empty ones, default store for no subject is 'Tree Doctor Examp'
    terms = Term.objects.filter(content__exact='')
    
    total = terms.count()
    print(f"총 {total}개의 설명 없는 용어 발견.")
    
    if total == 0:
        return

    # User confirmation
    confirm = input(f"{total}개 용어에 대해 AI 설명을 생성하시겠습니까? (y/N): ")
    if confirm.lower() != 'y':
        print("취소되었습니다.")
        return

    count_success = 0
    count_fail = 0
    
    for i, term in enumerate(terms, 1):
        print(f"[{i}/{total}] '{term.word}' 처리 중...", end=" ")
        
        try:
            # Determine Store
            target_store = "Tree Doctor Examp"
            subject = term.subjects.first()
            if subject:
                target_store = subject.name
                
            # Check store availability
            if target_store not in manager.stores:
                # If subject store not found, fallback to 'Tree Doctor Examp' or skip?
                # Usually sync should have handled it if files exist.
                # If strictly needed, we can specific check.
                pass
            
            # Query
            query = f"'{term.word}'에 대해 설명해줘."
            response_text = manager.query_store(target_store, query)
            
            if response_text and "No valid (ACTIVE) files found" not in response_text and "Store is empty" not in response_text:
                term.content = response_text
                term.save()
                print("✅ 완료")
                count_success += 1
            else:
                print(f"⚠️ 실패/내용없음 - {response_text[:50]}...")
                count_fail += 1
            
            # Rate limiting
            time.sleep(2) 
            
        except Exception as e:
            print(f"❌ 오류: {e}")
            count_fail += 1
            time.sleep(5)

    print("-" * 50)
    print(f"작업 완료. 성공: {count_success}, 실패: {count_fail}")

if __name__ == "__main__":
    main()
