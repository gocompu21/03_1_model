
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
    
    # 1. 대상 용어 조회 (content가 비어있는 것)
    terms = Term.objects.filter(content__exact='')
    total = terms.count()
    print(f"총 {total}개의 설명 없는 용어 발견.")
    
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
    
    # 타겟 스토어 (수목병리학 고정)
    target_store = "수목병리학"
    
    # 스토어가 없을 때만 동기화
    if target_store not in manager.stores or not manager.stores[target_store]:
        print("🔄 스토어 동기화 중...")
        manager.sync_all_stores()
    print(f"✅ 스토어 준비 완료: {target_store}")
    print("=" * 50)

    # 3. 처리
    count_success = 0
    count_fail = 0
    
    for idx, term in enumerate(terms, 1):
        try:
            prompt = f"{term.word}에 대해 설명해주세요."
            print(f"[{idx}/{total}] 조회 중: {term.word}")
            
            response_text = manager.query_store(target_store, prompt)
            
            # 오류 응답이 아닌 경우에만 업데이트
            if "429" not in response_text and "Error" not in response_text and len(response_text) > 100:
                term.content = response_text
                term.save()
                count_success += 1
                print(f"  -> 업데이트 완료 ({len(response_text)}자)")
            else:
                count_fail += 1
                print(f"  -> 오류: {response_text[:50] if response_text else 'None'}...")
                
        except Exception as e:
            print(f"  -> 예외: {e}")
            count_fail += 1
        
        # API 할당량 초과 방지를 위한 대기 (항상 60초)
        print(f"  -> 60초 대기...")
        time.sleep(60)

    print("=" * 50)
    print(f"작업 완료. 성공: {count_success}, 실패: {count_fail}")

if __name__ == "__main__":
    main()
