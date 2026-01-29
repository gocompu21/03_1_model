"""
산림토양학 용어 - 기출문제 연결 스크립트
문제 본문, 보기, 기본서 해설에서 용어를 찾아 TermReference 생성

서버에서 실행:
    python link_soil_terms.py --dry-run   # 미리보기
    python link_soil_terms.py             # 실제 연결
"""
import os
import sys
import re
import django

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from glossary.models import Term, TermReference, Subject
from exam.models import Question, Subject as ExamSubject

SUBJECT_NAME = "산림토양학"

def build_pattern_and_map(subject_name):
    """과목별 용어 패턴 생성"""
    terms = Term.objects.filter(subjects__name=subject_name).values('id', 'word')
    if not terms:
        return None, {}
    
    # 긴 단어 우선 정렬 (매칭 우선순위)
    sorted_terms = sorted(terms, key=lambda t: len(t['word']), reverse=True)
    term_map = {t['word']: t['id'] for t in sorted_terms}
    
    # 정규식 패턴 생성 (이스케이프 처리)
    words = [re.escape(t['word']) for t in sorted_terms]
    # 단어 경계 없이 단순 포함 여부 확인 (수목생리학/해충학 로직과 동일)
    pattern = re.compile('|'.join(words))
    
    return pattern, term_map

def get_question_text(question):
    """문제에서 검색할 텍스트 추출"""
    parts = [question.content or '']
    
    for i in range(1, 6):
        choice = getattr(question, f'choice{i}', '') or ''
        parts.append(choice)
    
    # 기본서 해설 (textbook_chat)
    if question.textbook_chat:
        parts.append(question.textbook_chat)
    
    return ' '.join(parts)

def main():
    dry_run = '--dry-run' in sys.argv
    
    print(f"=== {SUBJECT_NAME} 용어 - 기출문제 연결 스크립트 ===")
    if dry_run:
        print("[!] Preview mode (no changes)")
    print()
    
    # 1. 용어 준비
    pattern, term_map = build_pattern_and_map(SUBJECT_NAME)
    if not pattern:
        print(f"[X] {SUBJECT_NAME} terms not found in Glossary")
        return
    
    print(f"[*] Glossary Terms: {len(term_map)}")
    
    # 2. 문제 준비 (이름으로 매칭)
    try:
        exam_subject = ExamSubject.objects.get(name=SUBJECT_NAME)
        print(f"[*] Found Exam Subject: {exam_subject.name} (ID: {exam_subject.id})")
    except ExamSubject.DoesNotExist:
        print(f"[X] Exam Subject '{SUBJECT_NAME}' not found")
        # 혹시 이름이 다를 수 있으니 확인용
        print("Available Exam Subjects:", list(ExamSubject.objects.values_list('name', flat=True)))
        return
    
    questions = Question.objects.filter(subject=exam_subject)
    print(f"[*] Exam Questions: {questions.count()}")
    print()
    
    created_count = 0
    skipped_count = 0
    link_details = []
    
    # 3. 매칭 및 연결
    for question in questions:
        text = get_question_text(question)
        
        # 텍스트에서 용어 찾기
        found_terms = set()
        for match in pattern.finditer(text):
            term_word = match.group(0)
            term_id = term_map.get(term_word)
            if term_id:
                found_terms.add((term_id, term_word))
        
        # TermReference 생성
        for term_id, term_word in found_terms:
            source_title = f"{question.exam.round_number}회 {question.number}번"
            
            # 중복 체크
            exists = TermReference.objects.filter(
                term_id=term_id,
                source_type='question',
                source_id=question.id
            ).exists()
            
            if exists:
                skipped_count += 1
            else:
                if not dry_run:
                    TermReference.objects.create(
                        term_id=term_id,
                        source_type='question',
                        source_id=question.id,
                        source_title=source_title
                    )
                created_count += 1
                link_details.append({
                    'term': term_word,
                    'question': source_title
                })
    
    print(f"[+] New links: {created_count}")
    print(f"[-] Already exists: {skipped_count}")
    
    if link_details and len(link_details) <= 20:
        print("\n--- Details ---")
        for item in link_details:
            print(f"  {item['term']} <- {item['question']}")
    elif link_details:
        print(f"\n--- Details (First 20) ---")
        for item in link_details[:20]:
            print(f"  {item['term']} <- {item['question']}")
        print(f"  ... and {len(link_details) - 20} more")
    
    if dry_run:
        print("\n[!] To apply changes: python link_soil_terms.py")
    else:
        print(f"\n[OK] Completed!")

if __name__ == "__main__":
    main()
