
import os
import sys
import django
import time

# Django setup
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from glossary.models import Term, Subject
from fileSearchStore import GeminiStoreManager

def main():
    print("=== 수목생리학 용어 설명 일괄 채우기 (Gemini API) ===")
    
    target_subject_name = "수목생리학"
    
    # Check subject existence
    try:
        subject = Subject.objects.get(name=target_subject_name)
    except Subject.DoesNotExist:
        print(f"Error: Subject '{target_subject_name}' not found.")
        return

    # 1. 대상 용어 조회 (수목생리학 과목이면서 content가 비어있는 것)
    terms = Term.objects.filter(subjects=subject, content__exact='')
    total = terms.count()
    print(f"'{target_subject_name}' 과목의 설명 없는 용어: {total}개")
    
    if total == 0:
        print("업데이트할 용어가 없습니다.")
        return

    # 사용자 확인
    confirm = input(f"{total}개 용어에 대해 AI 설명을 생성하시겠습니까? (y/N): ")
    if confirm.lower() != 'y':
        print("취소되었습니다.")
        return

    # 2. GeminiStoreManager 초기화
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in settings.")
        return

    manager = GeminiStoreManager(api_key=api_key)
    print("✅ GeminiStoreManager initialized.")
    
    # 타겟 스토어
    target_store = target_subject_name
    
    # 스토어가 없을 때만 동기화
    if target_store not in manager.stores or not manager.stores[target_store]:
        print(f"🔄 스토어 '{target_store}' 동기화 및 확인 중...")
        manager.sync_all_stores()
        
    if target_store not in manager.stores:
         print(f"⚠️ Warning: Store '{target_store}' not found in Gemini stores. Using general query or creating new store may be needed.")
         # Proceed anyway, query_store might handle it or fail gracefully
    
    print(f"✅ 스토어 준비 완료: {target_store}")
    print("=" * 50)

    # 3. 처리
    count_success = 0
    count_fail = 0
    
    # iterator()를 사용하여 메모리 효율 개선
    for idx, term in enumerate(terms.iterator(), 1):
        try:
            prompt = f"'{term.word}'에 대해 수목생리학 관점에서 자세히 설명해줘."
            print(f"[{idx}/{total}] 조회 중: {term.word}")
            
            response_text = manager.query_store(target_store, prompt)
            
            # 429 Resource Exhausted (Quota limit) check
            if "429" in response_text or "Resource has been exhausted" in response_text:
                print("  -> ⚠️ Quota Exceeded (429). Waiting 5 minutes (300s) cooldown...")
                count_fail += 1
                time.sleep(300)
                continue

            # 기본 검증
            if "Error" not in response_text and len(response_text) > 50:
                # 출처 표기 추가
                term.content = f"{response_text}\n\n---\n### 기본서 발췌 ({target_store})"
                term.save()
                count_success += 1
                print(f"  -> 업데이트 완료 ({len(response_text)}자)")
            else:
                count_fail += 1
                print(f"  -> 오류/내용부족: {response_text[:50] if response_text else 'None'}...")
                
        except KeyboardInterrupt:
            print("\n⛔ 작업이 중단되었습니다.")
            break
        except Exception as e:
            print(f"  -> 예외: {e}")
            count_fail += 1
        
        # API 할당량 초과 방지를 위한 대기 (안정성을 위해 15~20초 권장, 여기서는 기존대로 60초 유지하거나 조정)
        # 15 RPM limits -> 60/15 = 4 seconds delay is minimum. To be safe, 10s.
        # User's previous script had 60s. I will stick to a safer 10s if paid, but let's use 20s to be safe for free tier? 
        # Actually previous script had 60s. I'll keep it fairly conservative but faster than 60s if possible.
        # Let's use 15s.
        print(f"  -> 60초 대기...")
        time.sleep(60)

    print("=" * 50)
    print(f"작업 완료. 성공: {count_success}, 실패: {count_fail}")

if __name__ == "__main__":
    main()
