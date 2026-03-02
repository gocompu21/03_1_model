"""12회 기출문제 용어 연결 스크립트
5개 과목 전체의 12회 문제를 용어사전과 연결합니다.

사용법:
    python link_round12_terms.py --dry-run   # 미리보기
    python link_round12_terms.py             # 실제 연결
"""
import os, sys, re, io, django

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from glossary.models import Term, TermReference, Subject as GlossarySubject
from exam.models import Question, Subject as ExamSubject, Exam

ROUND = 12


def build_pattern_and_map(subject_name):
    """과목별 용어 패턴 생성"""
    terms = Term.objects.filter(subjects__name=subject_name).values('id', 'word')
    if not terms:
        return None, {}
    sorted_terms = sorted(terms, key=lambda t: len(t['word']), reverse=True)
    term_map = {t['word']: t['id'] for t in sorted_terms}
    words = [re.escape(t['word']) for t in sorted_terms]
    pattern = re.compile('|'.join(words))
    return pattern, term_map


def get_question_text(question):
    """문제에서 검색할 텍스트 추출"""
    parts = [question.content or '']
    for i in range(1, 6):
        choice = getattr(question, f'choice{i}', '') or ''
        parts.append(choice)
    # 기본서 해설
    if hasattr(question, 'textbook_chat') and question.textbook_chat:
        parts.append(question.textbook_chat)
    # 일반 해설
    if hasattr(question, 'general_chat') and question.general_chat:
        parts.append(question.general_chat)
    return ' '.join(parts)


def main():
    dry_run = '--dry-run' in sys.argv

    print(f"=== {ROUND}회 기출문제 용어 연결 ===")
    if dry_run:
        print("[!] Preview mode (no changes)\n")

    try:
        exam = Exam.objects.get(round_number=ROUND)
    except Exam.DoesNotExist:
        print(f"[X] {ROUND}회 시험이 없습니다")
        return

    subjects = ["수목병리학", "수목해충학", "수목생리학", "산림토양학", "수목관리학"]
    total_created = 0
    total_skipped = 0

    for subject_name in subjects:
        print(f"\n--- {subject_name} ---")

        # 용어 패턴
        pattern, term_map = build_pattern_and_map(subject_name)
        if not pattern:
            print(f"  [X] 용어 없음")
            continue
        print(f"  용어 수: {len(term_map)}")

        # 해당 과목 12회 문제
        try:
            exam_subject = ExamSubject.objects.get(name=subject_name)
        except ExamSubject.DoesNotExist:
            print(f"  [X] 시험 과목 없음")
            continue

        questions = Question.objects.filter(exam=exam, subject=exam_subject)
        print(f"  문제 수: {questions.count()}")

        created = 0
        skipped = 0

        for question in questions:
            text = get_question_text(question)
            found_terms = set()
            for match in pattern.finditer(text):
                term_word = match.group(0)
                term_id = term_map.get(term_word)
                if term_id:
                    found_terms.add((term_id, term_word))

            for term_id, term_word in found_terms:
                source_title = f"{ROUND}회 {question.number}번"
                exists = TermReference.objects.filter(
                    term_id=term_id,
                    source_type='question',
                    source_id=question.id
                ).exists()

                if exists:
                    skipped += 1
                else:
                    if not dry_run:
                        TermReference.objects.create(
                            term_id=term_id,
                            source_type='question',
                            source_id=question.id,
                            source_title=source_title
                        )
                    created += 1

        print(f"  [+] 새 연결: {created}개")
        if skipped:
            print(f"  [-] 이미 존재: {skipped}개")
        total_created += created
        total_skipped += skipped

    print(f"\n{'='*40}")
    print(f"합계: 새 연결 {total_created}개, 이미 존재 {total_skipped}개")
    if dry_run:
        print(f"\n[!] 실제 적용: python link_round12_terms.py")
    else:
        print(f"\n[OK] {total_created}개 연결 완료!")


if __name__ == "__main__":
    main()
