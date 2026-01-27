
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

    # 사용자 확인 (자동 모드 지원)
    if '--auto' in sys.argv:
        print("⚡ 자동 모드: 사용자 확인을 건너뜁니다.")
    else:
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

    # 결과 저장용 리스트
    results = []
    output_file = "physiology_explanations.json"
    
    # 기존 파일이 있다면 로드해서 이어서 작업
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            print(f"📂 기존 파일 로드됨: {len(results)}개 항목")
            # 이미 처리된 용어는 건너뛰기 위한 집합
            processed_words = set(item['word'] for item in results)
        except Exception as e:
            print(f"⚠️ 기존 파일 로드 실패: {e}")
            processed_words = set()
    else:
        processed_words = set()

    # iterator()를 사용하여 메모리 효율 개선
    for idx, term in enumerate(terms.iterator(), 1):
        if term.word in processed_words:
            print(f"[{idx}/{total}] 이미 처리됨 (건너뜀): {term.word}")
            continue

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
                # 결과 리스트에 추가 (DB 저장 X)
                explanation = f"{response_text}\n\n---\n### 기본서 발췌 ({target_store})"
                result_item = {
                    'term_id': term.id,
                    'word': term.word,
                    'content': explanation
                }
                results.append(result_item)
                processed_words.add(term.word)
                
                # 중간 저장 (데이터 유실 방지)
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                    
                count_success += 1
                print(f"  -> 파일 저장 완료 ({len(response_text)}자)")
            else:
                count_fail += 1
                print(f"  -> 오류/내용부족: {response_text[:50] if response_text else 'None'}...")
                
        except KeyboardInterrupt:
            print("\n⛔ 작업이 중단되었습니다.")
            break
        except Exception as e:
            print(f"  -> 예외: {e}")
            count_fail += 1
        
        # API 할당량 초과 방지를 위한 대기
        print(f"  -> 60초 대기...")
        time.sleep(60)

    print("=" * 50)
    print(f"작업 완료. 성공: {count_success}, 실패: {count_fail}")
    print(f"결과 파일: {output_file}")

if __name__ == "__main__":
    main()
