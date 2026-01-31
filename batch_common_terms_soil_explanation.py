"""
91개 공통 용어(산림토양학 + 수목생리학)에 대해
산림토양학 기본서에서 설명을 추출하여 JSON으로 저장하는 스크립트
"""
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
    print("=== 공통 용어(산림토양학+수목생리학) 산림토양학 설명 추출 스크립트 ===")

    # 과목 가져오기
    try:
        soil_subject = Subject.objects.get(name="산림토양학")
        physio_subject = Subject.objects.get(name="수목생리학")
    except Subject.DoesNotExist as e:
        print(f"Error: 과목을 찾을 수 없습니다. {e}")
        return

    print(f"산림토양학: {soil_subject}")
    print(f"수목생리학: {physio_subject}")

    # 91개 공통 용어 가져오기
    common_terms_qs = Term.objects.filter(
        subjects=soil_subject
    ).filter(
        subjects=physio_subject
    ).values('id', 'word')

    term_list = list(common_terms_qs)

    # DB 연결 해제
    django.db.connections.close_all()
    print(">>> DB 연결 해제됨 (Lock Free).")

    total = len(term_list)
    print(f"\n공통 용어 개수: {total}개")

    if total == 0:
        print("작업할 용어가 없습니다.")
        return

    # 사용자 확인
    if '--auto' in sys.argv:
        print("자동 모드: 사용자 확인을 건너뜁니다.")
    else:
        confirm = input(f"{total}개 공통 용어에 대해 산림토양학 설명을 추출하시겠습니까? (y/N): ")
        if confirm.lower() != 'y':
            print("취소되었습니다.")
            return

    # GeminiStoreManager 초기화
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        print("Error: GEMINI_API_KEY not found in settings.")
        return

    manager = GeminiStoreManager(api_key=api_key)
    print("GeminiStoreManager initialized.")

    target_store = "산림토양학"

    if target_store not in manager.stores or not manager.stores[target_store]:
        print(f"스토어 '{target_store}' 동기화 및 확인 중...")
        manager.sync_all_stores()

    print(f"스토어 준비: {target_store}")
    print("=" * 50)

    # 결과 저장용
    results = []
    output_file = "common_terms_soil_explanations.json"
    processed_words = set()

    # 기존 파일이 있으면 로드
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            processed_words = set(item['word'] for item in results)
            print(f"기존 파일 로드됨: {len(results)}개 항목")
        except Exception as e:
            print(f"기존 파일 로드 실패: {e}")
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
            # 프롬프트: 산림토양학적 관점 강조
            prompt = f"'{term_word}'에 대해 산림토양학적 관점에서 설명해줘. 수목생리학과 구분되는 토양학적 특성을 중심으로."
            print(f"[{idx}/{total}] 조회 중: {term_word}")

            response_text = manager.query_store(target_store, prompt)

            if "Store is empty" in response_text or "No valid" in response_text:
                print("  -> 스토어 문제. 재시도...")
                time.sleep(5)
                response_text = manager.query_store(target_store, prompt)

            if "429" in response_text or "Resource has been exhausted" in response_text:
                print("  -> Quota Exceeded (429). Waiting 60s...")
                time.sleep(60)
                count_fail += 1
                continue

            if "Error" not in response_text and len(response_text) > 50:
                result_item = {
                    'term_id': term_id,
                    'word': term_word,
                    'content': response_text
                }
                results.append(result_item)
                processed_words.add(term_word)

                # 매번 저장 (중단 대비)
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)

                now_str = time.strftime("%H:%M:%S")
                count_success += 1
                print(f"  -> [{now_str}] 저장 완료 ({len(response_text)}자)")
            else:
                count_fail += 1
                print(f"  -> 내용 부족/오류: {response_text[:50]}...")

        except KeyboardInterrupt:
            print("\n작업 중단됨.")
            break
        except Exception as e:
            print(f"  -> 예외: {e}")
            count_fail += 1

        # API 호출 간격 (Rate Limit 대비)
        print(f"  -> 60초 대기...")
        time.sleep(60)

    print("=" * 50)
    print(f"작업 완료. 성공: {count_success}, 실패: {count_fail}")
    print(f"결과 파일: {output_file}")


if __name__ == "__main__":
    main()
