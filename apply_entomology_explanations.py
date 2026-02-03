# -*- coding: utf-8 -*-
"""
수목해충학 용어 설명 JSON을 DB에 적용하는 스크립트

사용법:
  python apply_entomology_explanations.py                    # 대화형 모드
  python apply_entomology_explanations.py --auto             # 자동 모드
  python apply_entomology_explanations.py --file custom.json # 다른 파일 지정
"""
import os
import sys
import json

# Django setup
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from glossary.models import Term


def main():
    print("=== 수목해충학 용어 설명 DB 적용 ===")

    # 파일 경로 설정
    input_file = "entomology_explanations.json"
    for i, arg in enumerate(sys.argv):
        if arg == '--file' and i + 1 < len(sys.argv):
            input_file = sys.argv[i + 1]

    if not os.path.exists(input_file):
        print(f"❌ Error: 파일을 찾을 수 없습니다: {input_file}")
        return

    # JSON 로드
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    total = len(data)
    print(f"📂 로드된 항목: {total}개")

    if total == 0:
        print("적용할 항목이 없습니다.")
        return

    # 샘플 출력
    print("\n--- 샘플 (처음 3개) ---")
    for item in data[:3]:
        print(f"  [{item['term_id']}] {item['word']}: {item['content'][:80]}...")
    print("---\n")

    # 사용자 확인
    if '--auto' not in sys.argv:
        confirm = input(f"{total}개 용어를 DB에 적용하시겠습니까? (y/N): ")
        if confirm.lower() != 'y':
            print("취소되었습니다.")
            return

    # DB 업데이트
    count_success = 0
    count_fail = 0

    for item in data:
        term_id = item['term_id']
        word = item['word']
        content = item['content']

        try:
            term = Term.objects.get(id=term_id)

            # 기존 내용이 있으면 추가, 없으면 대체
            if term.content and len(term.content) > 100:
                # 이미 충분한 내용이 있으면 건너뜀
                print(f"  [{term_id}] {word}: 이미 내용 있음 (건너뜀)")
                continue

            term.content = content
            term.save()
            count_success += 1
            print(f"  [{term_id}] {word}: ✅ 업데이트 완료")

        except Term.DoesNotExist:
            print(f"  [{term_id}] {word}: ❌ 용어 없음")
            count_fail += 1
        except Exception as e:
            print(f"  [{term_id}] {word}: ❌ 오류 - {e}")
            count_fail += 1

    print("\n" + "=" * 50)
    print(f"작업 완료. 성공: {count_success}, 실패: {count_fail}")


if __name__ == "__main__":
    main()
