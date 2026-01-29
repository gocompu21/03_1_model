
import os
import sys
import django
import time
import json

# Django setup
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from glossary.models import Term, Subject
from fileSearchStore import GeminiStoreManager

def main():
    print("=== 산림토양학 용어(기존 내용 보유) 설명 추가 스크립트 (Gemini API / No-Lock) ===")
    
    target_subject_name = "산림토양학"
    
    # Check subject existence
    try:
        subject = Subject.objects.get(name=target_subject_name)
    except Subject.DoesNotExist:
        print(f"Error: Subject '{target_subject_name}' not found.")
        return

    # 1. DB에서 필요한 데이터만 메모리로 로드
    print(">>> DB에서 대상 용어(내용이 이미 있는 용어) 목록을 가져오는 중...")
    
    # 수정 핵심: 내용이 있는 용어만 대상 (exclude content='')
    terms_qs = Term.objects.filter(subjects=subject).exclude(content__exact='').values('id', 'word')
    term_list = list(terms_qs)
    
    # DB 연결 강제 종료
    django.db.connections.close_all()
    print(">>> DB 연결 해제됨 (Lock Free).")
    
    total = len(term_list)
    print(f"'{target_subject_name}' 과목의 이미 내용이 있는 용어: {total}개")
    
    if total == 0:
        print("작업할 용어가 없습니다.")
        return

    # 사용자 확인
    if '--auto' in sys.argv:
        print("⚡ 자동 모드: 사용자 확인을 건너뜁니다.")
    else:
        confirm = input(f"{total}개 용어에 대해 산림토양학적 설명을 추가 생성하시겠습니까? (y/N): ")
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
    
    target_store = target_subject_name
    
    if target_store not in manager.stores or not manager.stores[target_store]:
        print(f"🔄 스토어 '{target_store}' 동기화 및 확인 중...")
        manager.sync_all_stores()
    
    print(f"✅ 스토어 준비: {target_store}")
    print("=" * 50)

    # 결과 저장용 리스트
    results = []
    output_file = "soil_explanations_existing.json"  # 파일명 변경
    processed_words = set()
    
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            processed_words = set(item['word'] for item in results)
            print(f"📂 기존 파일 로드됨: {len(results)}개 항목")
        except Exception as e:
            print(f"⚠️ 기존 파일 로드 실패: {e}")
            processed_words = set()

    count_success = 0
    count_fail = 0

    for idx, term_data in enumerate(term_list, 1):
        term_id = term_data['id']
        term_word = term_data['word']
        
        if term_word in processed_words:
            print(f"[{idx}/{total}] 이미 처리됨 (건너뜀): {term_word}")
            continue

        try:
            # 프롬프트: 다른 관점과의 차별화 강조
            prompt = f"'{term_word}'에 대해 산림토양학적 관점에서만 설명해줘. (다른 과목의 정의와 구분되도록)"
            print(f"[{idx}/{total}] 조회 중: {term_word}")
            
            response_text = manager.query_store(target_store, prompt)
            
            if "Store is empty" in response_text or "No valid" in response_text:
                print("  -> ⚠️ 스토어 문제. 재시도 로직...")
                time.sleep(5)
                response_text = manager.query_store(target_store, prompt)
            
            if "429" in response_text or "Resource has been exhausted" in response_text:
                print("  -> ⚠️ Quota Exceeded (429). Waiting 60s...")
                time.sleep(60)
                count_fail += 1
                continue

            if "Error" not in response_text and len(response_text) > 50:
                explanation = f"{response_text}\n\n---\n### 기본서 발췌 ({target_store})"
                result_item = {
                    'term_id': term_id,
                    'word': term_word,
                    'content': explanation
                }
                results.append(result_item)
                processed_words.add(term_word)
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                    
                count_success += 1
                print(f"  -> 저장 완료")
            else:
                count_fail += 1
                print(f"  -> 내용 부족/오류: {response_text[:30]}...")
                
        except KeyboardInterrupt:
            print("\n⛔ 작업 중단됨.")
            break
        except Exception as e:
            print(f"  -> 예외: {e}")
            count_fail += 1
        
        # 딜레이 
        print(f"  -> 60초 대기...")
        time.sleep(60)

    print("=" * 50)
    print(f"작업 완료. 성공: {count_success}, 실패: {count_fail}")
    print(f"결과 파일: {output_file}")

if __name__ == "__main__":
    main()
