"""
common_terms_soil_explanations.json의 산림토양학 설명을
기존 Term의 content에 구분자로 추가하는 스크립트
"""
import os
import sys
import django
import json

# Django setup
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from glossary.models import Term


def main():
    print("=== 산림토양학 기본서 내용을 기존 용어 설명에 추가 ===")

    # JSON 파일 로드
    json_file = 'common_terms_soil_explanations.json'
    if not os.path.exists(json_file):
        print(f"Error: {json_file} 파일을 찾을 수 없습니다.")
        return

    with open(json_file, 'r', encoding='utf-8') as f:
        soil_data = json.load(f)

    print(f"로드된 용어: {len(soil_data)}개")

    # 구분자 정의: 내용 먼저, 그 다음 라벨을 하단에 배치 (위아래 줄, h3 크기)
    label = "\n\n---\n### 기본서 발췌 (산림토양학)\n---"

    # 사용자 확인
    if '--auto' not in sys.argv:
        confirm = input(f"{len(soil_data)}개 용어에 산림토양학 내용을 추가하시겠습니까? (y/N): ")
        if confirm.lower() != 'y':
            print("취소되었습니다.")
            return

    # 통계
    updated = 0
    skipped = 0
    not_found = 0

    for item in soil_data:
        term_id = item.get('term_id')
        word = item.get('word')
        soil_content = item.get('content', '')

        if not soil_content:
            skipped += 1
            print(f"[건너뜀] {word} - 내용 없음")
            continue

        try:
            term = Term.objects.get(id=term_id)

            # 이미 산림토양학 기본서 내용이 있는지 확인
            if "### 기본서 발췌 (산림토양학)" in term.content:
                skipped += 1
                print(f"[건너뜀] {word} - 이미 추가됨")
                continue

            # 기존 content에 내용 추가 후 라벨을 제일 하단에 배치
            term.content = term.content + "\n\n---\n" + soil_content + label
            term.save()

            updated += 1
            print(f"[업데이트] {word}")

        except Term.DoesNotExist:
            not_found += 1
            print(f"[없음] {word} (ID: {term_id}) - DB에 없음")
        except Exception as e:
            print(f"[에러] {word}: {e}")

    print("=" * 50)
    print(f"완료!")
    print(f"  업데이트: {updated}개")
    print(f"  건너뜀: {skipped}개")
    print(f"  찾지 못함: {not_found}개")


if __name__ == "__main__":
    main()
