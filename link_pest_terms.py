"""
수목해충학 용어 - 기출문제 연결 스크립트
문제 본문, 보기, 기본서 해설에서 용어를 찾아 TermReference 생성

서버에서 실행:
    python link_pest_terms.py --dry-run   # 미리보기
    python link_pest_terms.py             # 실제 연결
"""
import os
import sys
import re
import django

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from glossary.models import Term, TermReference
from exam.models import Question, Subject

SUBJECT_NAME = "수목해충학"

def build_pattern_and_map(subject_name):
    """과목별 용어 패턴 생성"""
    terms = Term.objects.filter(subjects__name=subject_name).values('id', 'word')
    if not terms:
        return None, {}
    
    # 긴 단어 우선
    sorted_terms = sorted(terms, key=lambda t: len(t['word']), reverse=True)
    term_map = {t['word']: t['id'] for t in sorted_terms}
    
    # 정규식 패턴 (단어 경계 없이, 그대로 매칭)
    words = [re.escape(t['word']) for t in sorted_terms]
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
    
    # 용어 패턴 생성
    pattern, term_map = build_pattern_and_map(SUBJECT_NAME)
    if not pattern:
        print(f"[X] {SUBJECT_NAME} - no terms found")
        return
    
    print(f"[*] {SUBJECT_NAME} terms: {len(term_map)}")
    
    # 해당 과목 문제 조회
    try:
        subject = Subject.objects.get(name=SUBJECT_NAME)
    except Subject.DoesNotExist:
        print(f"[X] {SUBJECT_NAME} subject not found")
        return
    
    questions = Question.objects.filter(subject=subject)
    print(f"[*] {SUBJECT_NAME} questions: {questions.count()}")
    print()
    
    created_count = 0
    skipped_count = 0
    link_details = []
    
    for question in questions:
        text = get_question_text(question)
        
        # 용어 매칭
        found_terms = set()
        for match in pattern.finditer(text):
            term_word = match.group(0)
            term_id = term_map.get(term_word)
            if term_id:
                found_terms.add((term_id, term_word))
        
        for term_id, term_word in found_terms:
            # 이미 존재하는지 확인
            source_title = f"{question.exam.round_number}회 {question.number}번"
            
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
        print("\n--- 연결 상세 ---")
        for item in link_details:
            print(f"  {item['term']} ← {item['question']}")
    elif link_details:
        print(f"\n--- 연결 상세 (처음 20개) ---")
        for item in link_details[:20]:
            print(f"  {item['term']} ← {item['question']}")
        print(f"  ... 외 {len(link_details) - 20}개")
    
    if dry_run:
        print("\n[!] To apply: python link_pest_terms.py")
    else:
        print(f"\n[OK] {created_count} links created!")

if __name__ == "__main__":
    main()
