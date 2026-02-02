# -*- coding: utf-8 -*-
"""
형태소 분석을 이용한 용어-기출문제 연결 스크립트
- KoNLPy Okt를 사용하여 문제에서 명사 추출
- 추출된 명사와 용어를 비교하여 연결

사용법:
  python link_terms_morpheme.py --subject=수목관리학
  python link_terms_morpheme.py --subject=수목관리학 --dry-run  # 테스트만
  python link_terms_morpheme.py --subject=수목관리학 --add-subject  # 과목에도 추가
"""
import os
import sys
import django

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from konlpy.tag import Okt
from glossary.models import Term, Subject as GlossarySubject, TermReference
from exam.models import Question, Subject as ExamSubject, Exam


def main():
    # 인자 파싱
    target_subject = "수목관리학"
    dry_run = '--dry-run' in sys.argv
    add_subject = '--add-subject' in sys.argv

    for arg in sys.argv:
        if arg.startswith('--subject='):
            target_subject = arg.split('=')[1]

    print(f"=== 형태소 분석 기반 용어 연결 ===")
    print(f"대상 과목: {target_subject}")
    print(f"Dry run: {dry_run}")
    print(f"과목 추가: {add_subject}")
    print()

    # 형태소 분석기 초기화
    print("형태소 분석기 초기화 중...")
    okt = Okt()

    # 과목 조회
    try:
        exam_subject = ExamSubject.objects.get(name=target_subject)
        glossary_subject = GlossarySubject.objects.get(name=target_subject)
    except Exception as e:
        print(f"Error: 과목을 찾을 수 없습니다 - {e}")
        return

    # 다른 과목의 용어 중 현재 과목에 없는 것들
    other_terms = Term.objects.exclude(subjects=glossary_subject)
    term_dict = {t.word: t for t in other_terms}
    term_words = set(term_dict.keys())

    print(f"다른 과목 용어 수: {len(term_words)}")

    # 대상 과목의 기출문제
    questions = Question.objects.filter(subject=exam_subject)
    print(f"기출문제 수: {questions.count()}")
    print()

    # 결과 저장
    results = []

    for q in questions:
        # 문제 텍스트 (지문 + 보기)
        text = f"{q.content} {q.choice1} {q.choice2} {q.choice3} {q.choice4} {q.choice5}"

        # 형태소 분석으로 명사 추출
        nouns = set(okt.nouns(text))

        # 복합명사 처리 - 원본 텍스트에서 용어 직접 검색도 병행
        # (형태소 분석이 복합명사를 분리할 수 있으므로)
        found_terms = set()

        # 1. 형태소 분석 결과에서 찾기
        for noun in nouns:
            if noun in term_words and len(noun) >= 2:
                found_terms.add(noun)

        # 2. 원본 텍스트에서 직접 검색 (3글자 이상 용어만)
        for term_word in term_words:
            if len(term_word) >= 3 and term_word in text:
                found_terms.add(term_word)

        # 결과 저장
        for term_word in found_terms:
            results.append({
                'term_word': term_word,
                'term': term_dict[term_word],
                'question': q,
                'round': q.exam.round_number,
                'number': q.number
            })

    # 중복 제거
    seen = set()
    unique_results = []
    for r in results:
        key = (r['term_word'], r['question'].id)
        if key not in seen:
            seen.add(key)
            unique_results.append(r)

    # 정렬
    unique_results.sort(key=lambda x: (x['term_word'], x['round'], x['number']))

    print(f"발견된 용어-문제 연결: {len(unique_results)}개")
    print()

    if dry_run:
        # 샘플 출력
        print("--- 샘플 (처음 30개) ---")
        for r in unique_results[:30]:
            print(f"  {r['term_word']:25} | {r['round']}회 {r['number']}번")
        if len(unique_results) > 30:
            print(f"  ... 외 {len(unique_results) - 30}개")
        print()
        print("실제 적용하려면 --dry-run 옵션을 제거하세요.")
        return

    # DB 적용
    print("DB에 적용 중...")
    count_term_added = 0
    count_ref_created = 0
    count_ref_exists = 0

    processed_terms = set()

    for r in unique_results:
        term = r['term']
        question = r['question']

        # 과목 추가 (옵션)
        if add_subject and r['term_word'] not in processed_terms:
            if glossary_subject not in term.subjects.all():
                term.subjects.add(glossary_subject)
                count_term_added += 1
            processed_terms.add(r['term_word'])

        # TermReference 생성
        ref, created = TermReference.objects.get_or_create(
            term=term,
            source_type='question',
            source_id=question.id,
            defaults={'source_title': f"{r['round']}회 {r['number']}번"}
        )

        if created:
            count_ref_created += 1
        else:
            count_ref_exists += 1

    print()
    print("=== 완료 ===")
    print(f"  과목에 추가된 용어: {count_term_added}")
    print(f"  생성된 연결: {count_ref_created}")
    print(f"  이미 존재: {count_ref_exists}")


if __name__ == "__main__":
    main()
