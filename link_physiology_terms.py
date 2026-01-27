import os
import django
import sys

# Django Setup
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from glossary.models import Term, TermReference
from exam.models import Question

def link_physiology_terms():
    # 1. 수목생리학 과목 필터링
    target_subject_name = "수목생리학"
    
    print(f"Adding links for subject: {target_subject_name}")
    
    # 2. 관련 용어 가져오기
    # glossary.models.Term -> subjects__name=target_subject_name
    terms = Term.objects.filter(subjects__name=target_subject_name).prefetch_related('subjects')
    
    # 3. 관련 문제 가져오기
    # exam.models.Question -> subject__name=target_subject_name
    questions = Question.objects.filter(subject__name=target_subject_name).select_related('exam')
    
    print(f"Target Terms: {terms.count()}")
    print(f"Target Questions: {questions.count()}")
    
    if terms.count() == 0 or questions.count() == 0:
        print("No terms or questions found. Please check data.")
        return

    # (Optional) 기존 수목생리학 관련 링크만 삭제하고 다시 할 수도 있지만, 
    # 여기서는 get_or_create로 중복 방지하며 추가만 함.
    # 안전하게 하려면: 해당 용어들에 대한 기존 'question' 타입 레퍼런스 삭제?
    # TermReference.objects.filter(term__in=terms, source_type='question').delete()
    # -> This ensures clean state for these terms.
    
    print("Clearing existing references for these terms to ensure fresh links...")
    deleted = TermReference.objects.filter(term__in=terms, source_type='question').delete()[0]
    print(f"Deleted {deleted} existing links.")

    total_links = 0
    terms_with_links = 0
    
    for term in terms:
        word = term.word
        # Skip empty words
        if not word.strip():
            continue
            
        found_questions = []
        
        for q in questions:
            # 문제 내용, 보기, 해설에서 검색
            search_texts = [
                q.content or '',
                q.choice1 or '', q.choice2 or '', q.choice3 or '', q.choice4 or '', q.choice5 or '',
                q.general_chat or '' # 해설도 포함
            ]
            
            # 용어가 포함된 문제 찾기
            if any(word in text for text in search_texts):
                found_questions.append(q)
        
        if found_questions:
            terms_with_links += 1
            # print(f"[{word}] {len(found_questions)} questions linked")
            
            for q in found_questions:
                source_title = f"{q.exam.round_number}회({q.number})"
                
                TermReference.objects.get_or_create(
                    term=term,
                    source_type='question',
                    source_id=q.pk,
                    defaults={
                        'source_title': source_title
                    }
                )
                total_links += 1
                
    print("=" * 50)
    print(f"Linking Completed for {target_subject_name}")
    print(f"Terms with links: {terms_with_links}")
    print(f"Total links created: {total_links}")

if __name__ == "__main__":
    link_physiology_terms()
