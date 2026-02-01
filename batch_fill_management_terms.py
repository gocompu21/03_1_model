# -*- coding: utf-8 -*-
"""
수목관리학(농약학) 용어 설명 일괄 채우기 스크립트
- Gemini API를 사용하여 기본서에서 용어 설명을 검색
- 결과를 JSON 파일로 저장 (중단 시 이어서 작업 가능)

사용법:
  python batch_fill_management_terms.py        # 대화형 모드
  python batch_fill_management_terms.py --auto # 자동 모드 (확인 없이 실행)
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
    print("=== 수목관리학 용어 설명 일괄 채우기 (Gemini API / No-Lock Version) ===")

    target_subject_name = "수목관리학"

    # Check subject existence
    try:
        subject = Subject.objects.get(name=target_subject_name)
    except Subject.DoesNotExist:
        print(f"Error: Subject '{target_subject_name}' not found.")
        return

    # 1. DB에서 필요한 데이터만 메모리로 로드 (Quick Fetch)
    print(">>> DB에서 대상 용어 목록을 가져오는 중...")

    # 내용이 비어있거나 100자 미만인 용어만 대상
    term_list = []
    for t in Term.objects.filter(subjects=subject).values('id', 'word', 'content'):
        if not t['content'] or len(t['content']) < 100:
            term_list.append(t)

    # DB 연결 강제 종료
    django.db.connections.close_all()
    print(">>> DB 연결 해제됨 (Lock Free).")

    total = len(term_list)
    print(f"'{target_subject_name}' 과목의 설명 필요 용어: {total}개")

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

    # 타겟 스토어 (수목관리학 기본서)
    target_store = target_subject_name

    # 메모리에서 스토어 이름만 사용, DB 접근 안함
    if target_store not in manager.stores or not manager.stores[target_store]:
        print(f"🔄 스토어 '{target_store}' 동기화 및 확인 중...")
        manager.sync_all_stores()

    if target_store not in manager.stores:
        print(f"⚠️ Warning: Store '{target_store}' not found in local_stores.json.")
        print("   사용 가능한 스토어 목록:")
        for store_name in manager.stores.keys():
            print(f"   - {store_name}")
        # 대체 스토어 이름 시도
        alt_stores = ["농약학", "Tree Doctor Examp"]
        for alt in alt_stores:
            if alt in manager.stores:
                target_store = alt
                print(f"   -> 대체 스토어 사용: {target_store}")
                break

    print(f"✅ 스토어 준비: {target_store}")
    print("=" * 50)

    # 결과 저장용 리스트
    results = []
    output_file = "management_explanations.json"
    processed_words = set()

    # 기존 파일이 있다면 로드해서 이어서 작업
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            processed_words = set(item['word'] for item in results)
            print(f"📂 기존 파일 로드됨: {len(results)}개 항목")
        except Exception as e:
            print(f"⚠️ 기존 파일 로드 실패: {e}")
            processed_words = set()

    # 통계 변수 초기화
    count_success = 0
    count_fail = 0
    count_skip = 0

    # 메모리에 로드된 리스트로 반복
    for idx, term_data in enumerate(term_list, 1):
        term_id = term_data['id']
        term_word = term_data['word']

        if term_word in processed_words:
            print(f"[{idx}/{total}] 이미 처리됨 (건너뜀): {term_word}")
            count_skip += 1
            continue

        try:
            # 프롬프트: 농약학/수목관리학 관점 강조
            prompt = f"'{term_word}'에 대해 농약학(수목관리학) 관점에서 자세히 설명해줘. 정의, 특징, 작용기작, 사용 예시 등을 포함해서 설명해줘."
            print(f"[{idx}/{total}] 조회 중: {term_word}")

            response_text = manager.query_store(target_store, prompt)

            # 오류 감지 및 자동 복구
            if "Store is empty" in response_text or "No valid" in response_text or "Store not found" in response_text:
                print("  -> ⚠️ 스토어 문제 발생. 전체 동기화 시도 중...")
                manager.sync_all_stores()
                time.sleep(5)
                # 단순 재시도
                print(f"  -> [{term_word}] 재시도 중...")
                response_text = manager.query_store(target_store, prompt)
                if "Store is empty" in response_text or "No valid" in response_text:
                    print("  -> ❌ 재시도 실패. 건너뜁니다.")
                    count_fail += 1
                    continue

            # Quota Check
            if "429" in response_text or "Resource has been exhausted" in response_text:
                print("  -> ⚠️ Quota Exceeded (429). Waiting 60s...")
                time.sleep(60)
                count_fail += 1
                continue

            # 결과 저장
            if "Error" not in response_text and len(response_text) > 50:
                explanation = f"{response_text}\n\n---\n### 기본서 발췌 ({target_store})"
                result_item = {
                    'term_id': term_id,
                    'word': term_word,
                    'content': explanation
                }
                results.append(result_item)
                processed_words.add(term_word)

                # 매번 파일에 저장 (중단 시 복구 가능)
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)

                now_str = time.strftime("%H:%M:%S")
                count_success += 1
                print(f"  -> [{now_str}] 저장 완료 ({len(response_text)}자)")
            else:
                count_fail += 1
                print(f"  -> 내용 부족/오류: {response_text[:50]}...")

        except KeyboardInterrupt:
            print("\n⛔ 작업 중단됨.")
            break
        except Exception as e:
            print(f"  -> 예외: {e}")
            count_fail += 1

        # 딜레이 (리소스 보호) - Rate limit 방지를 위해 60초 대기
        print(f"  -> 60초 대기...")
        time.sleep(60)

    print("=" * 50)
    print(f"작업 완료. 성공: {count_success}, 실패: {count_fail}, 건너뜀: {count_skip}")
    print(f"결과 파일: {output_file}")
    print("\n다음 단계: apply_management_explanations.py 실행하여 DB에 적용")


if __name__ == "__main__":
    main()
