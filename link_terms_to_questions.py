import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from glossary.models import Term, TermReference
from exam.models import Question

# 기존 question 타입 참조 삭제
deleted_count = TermReference.objects.filter(source_type='question').delete()[0]
print(f"기존 참조 삭제: {deleted_count}개")

# 모든 Term과 Question 가져오기
terms = Term.objects.prefetch_related('subjects').all()
questions = Question.objects.select_related('exam', 'subject').all()

print(f"용어: {terms.count()}개")
print(f"문제: {questions.count()}개")
print("=" * 50)

# 처리 카운트
total_links = 0
terms_with_links = 0

for term in terms:
    word = term.word
    # 용어의 과목들 가져오기
    term_subject_names = set(s.name for s in term.subjects.all())
    
    found_questions = []
    
    for q in questions:
        # 문제의 과목이 용어의 과목과 일치하는지 확인
        if q.subject.name not in term_subject_names:
            continue
        
        # 문제 내용, 보기, 해설에서 검색
        search_texts = [
            q.content or '',
            q.choice1 or '', q.choice2 or '', q.choice3 or '', q.choice4 or '', q.choice5 or '',
            # 해설 제외 (textbook_chat, general_chat)
        ]
        
        # 용어가 포함된 문제 찾기
        if any(word in text for text in search_texts):
            found_questions.append(q)
    
    if found_questions:
        terms_with_links += 1
        print(f"[{term.word}] ({', '.join(term_subject_names)}) {len(found_questions)}개 문제")
        
        for q in found_questions:
            # 회차 정보 생성
            source_title = f"{q.exam.round_number}회({q.number})"
            
            # TermReference 생성
            ref, created = TermReference.objects.get_or_create(
                term=term,
                source_type='question',
                source_id=q.pk,
                defaults={
                    'source_title': source_title
                }
            )
            if created:
                total_links += 1

print("=" * 50)
print(f"완료!")
print(f"  연결된 용어: {terms_with_links}개")
print(f"  생성된 링크: {total_links}개")
