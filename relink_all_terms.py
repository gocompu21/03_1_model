"""전 회차 용어 재연결 스크립트 (문제+보기만, 해설 제외)
기존 question 타입 TermReference를 모두 삭제하고 문제 지문+보기만으로 재생성합니다.

사용법:
    python relink_all_terms.py --dry-run   # 미리보기
    python relink_all_terms.py             # 실제 연결
"""
import os, sys, re, io, django

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from glossary.models import Term, TermReference, Subject as GlossarySubject
from exam.models import Question, Subject as ExamSubject, Exam

SUBJECTS = ["수목병리학", "수목해충학", "수목생리학", "산림토양학", "수목관리학"]


def build_pattern_and_map(subject_name):
    """과목별 용어 패턴 생성 (긴 용어 우선)"""
    terms = Term.objects.filter(subjects__name=subject_name).values('id', 'word')
    if not terms:
        return None, {}
    sorted_terms = sorted(terms, key=lambda t: len(t['word']), reverse=True)
    term_map = {t['word']: t['id'] for t in sorted_terms}
    words = [re.escape(t['word']) for t in sorted_terms]
    pattern = re.compile('|'.join(words))
    return pattern, term_map


def get_question_text(question):
    """문제 지문 + 보기만 추출 (해설 제외)"""
    parts = [question.content or '']
    for i in range(1, 6):
        choice = getattr(question, f'choice{i}', '') or ''
        parts.append(choice)
    return ' '.join(parts)


def main():
    dry_run = '--dry-run' in sys.argv

    print("=== 전 회차 용어 재연결 (문제+보기만) ===")
    if dry_run:
        print("[!] Preview mode (no changes)\n")

    # 1. 기존 question 타입 참조 전체 삭제
    old_count = TermReference.objects.filter(source_type='question').count()
    if old_count and not dry_run:
        TermReference.objects.filter(source_type='question').delete()
        print(f"[삭제] 기존 question 참조 {old_count:,}개 삭제\n")
    elif old_count:
        print(f"[삭제 예정] 기존 question 참조 {old_count:,}개\n")

    # 2. 과목별 용어 패턴 빌드
    patterns = {}
    for subject_name in SUBJECTS:
        pattern, term_map = build_pattern_and_map(subject_name)
        if pattern:
            patterns[subject_name] = (pattern, term_map)
            print(f"  {subject_name}: {len(term_map):,}개 용어")
    print()

    # 3. 전 회차 문제 순회
    grand_total = 0
    for exam in Exam.objects.all().order_by('round_number'):
        if exam.round_number == 0:
            continue
        round_total = 0

        for subject_name in SUBJECTS:
            if subject_name not in patterns:
                continue
            pattern, term_map = patterns[subject_name]

            try:
                exam_subject = ExamSubject.objects.get(name=subject_name)
            except ExamSubject.DoesNotExist:
                continue

            questions = Question.objects.filter(exam=exam, subject=exam_subject)
            created = 0

            for question in questions:
                text = get_question_text(question)
                found_terms = set()
                for match in pattern.finditer(text):
                    term_word = match.group(0)
                    term_id = term_map.get(term_word)
                    if term_id:
                        found_terms.add((term_id, term_word))

                for term_id, term_word in found_terms:
                    source_title = f"{exam.round_number}회 {question.number}번"
                    if not dry_run:
                        TermReference.objects.create(
                            term_id=term_id,
                            source_type='question',
                            source_id=question.id,
                            source_title=source_title
                        )
                    created += 1

            round_total += created

        print(f"  {exam.round_number}회: {round_total:,}개 연결")
        grand_total += round_total

    print(f"\n{'='*40}")
    print(f"합계: {grand_total:,}개 연결")
    if dry_run:
        print(f"\n[!] 실제 적용: python relink_all_terms.py")
    else:
        print(f"\n[OK] {grand_total:,}개 연결 완료!")


if __name__ == "__main__":
    main()
