"""
토양학 용어 DB 등록 스크립트

사용법:
    python import_soil_terms.py --dry-run   # 미리보기
    python import_soil_terms.py             # 실제 등록
"""
import os
import sys
import django

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from glossary.models import Term, Subject

SUBJECT_NAME = "산림토양학"
SOURCE_FILE = "soil_terms.txt"

def main():
    dry_run = '--dry-run' in sys.argv
    
    print(f"=== {SUBJECT_NAME} 용어 등록 스크립트 ===")
    if dry_run:
        print("[!] Preview mode (no changes)")
    
    # 0. 파일 읽기
    if not os.path.exists(SOURCE_FILE):
        print(f"[X] File not found: {SOURCE_FILE}")
        return

    with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 빈 줄 및 공백 제거
    terms_to_add = [line.strip() for line in lines if line.strip()]
    print(f"[*] Found {len(terms_to_add)} terms in file")
    
    # 1. 과목 생성/조회
    if dry_run:
        try:
            subject = Subject.objects.get(name=SUBJECT_NAME)
            print(f"[*] Existing subject: {subject.name}")
        except Subject.DoesNotExist:
            print(f"[+] Will create subject: {SUBJECT_NAME}")
            subject = None
    else:
        subject, created = Subject.objects.get_or_create(
            name=SUBJECT_NAME
        )
        if created:
            print(f"[+] Created subject: {subject.name}")
        else:
            print(f"[*] Found subject: {subject.name}")

    # 2. 용어 등록
    created_count = 0
    updated_count = 0
    
    for word in terms_to_add:
        if dry_run:
            # 존재 여부만 확인
            try:
                term = Term.objects.get(word=word)
                if subject and not term.subjects.filter(id=subject.id).exists():
                    print(f"  [U] {word} - add subject")
                else:
                    pass # 이미 과목도 연결됨
            except Term.DoesNotExist:
                print(f"  [+] {word} - new term")
            created_count += 1
            continue

        # 실제 등록
        term, created = Term.objects.get_or_create(word=word)
        
        # 과목 연결 check
        if not term.subjects.filter(id=subject.id).exists():
            term.subjects.add(subject)
            if created:
                created_count += 1
                # print(f"  [+] {word}")
            else:
                updated_count += 1
                # print(f"  [U] {word}")
        else:
            pass # 이미 연결됨

    if dry_run:
        print(f"\n[!] Preview: {len(terms_to_add)} terms will be processed")
        print("Run without --dry-run to apply changes")
    else:
        print(f"\n[OK] Processed {len(terms_to_add)} terms")
        print(f"  - New terms: {created_count}")
        print(f"  - Existing terms (linked to subject): {updated_count}")

if __name__ == "__main__":
    main()
