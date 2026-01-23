import os
import sys
import django
from tqdm import tqdm

# Django Setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from exam.models import Question, Subject
from glossary.models import Term, TermReference, Subject as GlossarySubject

def link_references():
    # 1. 수목해충학 과목
    try:
        glossary_subject = GlossarySubject.objects.get(name__contains='수목해충학')
        exam_subject = Subject.objects.get(name__contains='수목해충학')
    except Exception as e:
        print(f"과목 찾기 오류: {e}")
        return

    # 2. 용어 및 문제 가져오기
    terms = Term.objects.filter(subjects=glossary_subject)
    questions = Question.objects.filter(subject=exam_subject)
    
    print(f"용어: {terms.count()}개")
    print(f"문제: {questions.count()}개")
    
    # 3. 매칭 및 참조 생성
    # 메모리 최적화를 위해 용어를 리스트로 로드
    term_list = list(terms)
    
    created_count = 0
    
    for q in tqdm(questions, desc="문제 분석 중"):
        content = q.content
        # 보기 포함
        full_text = f"{content} {q.choice1} {q.choice2} {q.choice3} {q.choice4} {q.choice5}"
        
        for term in term_list:
            if term.word in full_text:
                # 참조 생성
                # source_type: 'question'
                # source_id: q.id
                # source_title: e.g. "5회 10번"
                
                title = f"{q.exam.round_number}회 {q.number}번"
                
                ref, created = TermReference.objects.get_or_create(
                    term=term,
                    source_type='question',
                    source_id=q.id,
                    defaults={'source_title': title}
                )
                
                if created:
                    created_count += 1
    
    print(f"참조 연결 완료. 신규 생성: {created_count}건")

if __name__ == "__main__":
    link_references()
