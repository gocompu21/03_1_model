
import os
import sys
import django
import re
from collections import Counter

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from exam.models import Question, Subject
from glossary.models import Term

def main():
    print("=== 산림토양학 미등록 용어 추출 ===")
    
    # 1. Subject ID for 산림토양학
    target_name = "산림토양학"
    # Try exact match first, then contains
    try:
        subject = Subject.objects.get(name=target_name)
    except Subject.DoesNotExist:
        subject = Subject.objects.filter(name__contains="토양").first()
    
    if not subject:
        print("산림토양학 과목을 찾을 수 없습니다.")
        return
        
    print(f"대상 과목: {subject.name} (ID: {subject.id})")
    
    # 2. Fetch Questions
    questions = Question.objects.filter(subject=subject)
    print(f"총 문제 수: {questions.count()}")
    
    # 3. Extract Candidates
    text_corpus = ""
    for q in questions:
        # Combine all text fields
        text_corpus += f" {q.content} {q.choice1} {q.choice2} {q.choice3} {q.choice4} {q.choice5}"
        # if q.explanation:
        #    text_corpus += f" {q.explanation}"
        
    # Regex Patterns
    # Pattern 1: 한글(영어/한자/숫자) -> '양이온교환용량(CEC)' capture '양이온교환용량'
    # Also capture the inside part if it's English -> 'CEC'
    pattern_bracket = r'([가-힣]+)\s*\(([\w\s\.-]+)\)'
    
    candidates = set()
    
    # Extract Parenthesis Patterns
    found_brackets = re.findall(pattern_bracket, text_corpus)
    print(f"괄호 패턴 발견 수: {len(found_brackets)}")
    
    for kor, inside in found_brackets:
        if len(kor) > 1:
            candidates.add(kor.strip())
        
        # If text inside parens is English word(s)
        if re.match(r'^[A-Za-z\s-]+$', inside):
            if len(inside) > 2: # Ignore single chars like (A) (B)
                candidates.add(inside.strip())
                
    # Also extracting standalone English capitalized words (acronyms or scientific names)
    # e.g. CEC, BS, pH, Al, Fe...
    # Avoid general english words if possible, but hard without dictionary.
    # Restrict to UpperCase or TitleCase
    pattern_eng_upper = r'\b[A-Z][a-zA-Z0-9-]{1,}\b'
    found_eng = re.findall(pattern_eng_upper, text_corpus)
    
    # Filter common garbage
    stopwords = {'The', 'And', 'Of', 'To', 'In', 'Is', 'Are'} 
    for eng in found_eng:
        if eng not in stopwords and len(eng) > 1:
             candidates.add(eng.strip())

    print(f"추출된 고유 후보 어휘 수: {len(candidates)}")
    
    # 4. Check against Term Database
    # Load all existing terms (flat list) to minimize DB hits
    existing_terms = set(Term.objects.values_list('word', flat=True))
    
    # Normalize for case-insensitive comparison
    existing_lower = set(t.lower() for t in existing_terms)
    
    missing_list = []
    
    for cand in candidates:
        if cand.lower() not in existing_lower:
            missing_list.append(cand)
            
    missing_list.sort()
    
    # Display Results
    print("\n" + "="*40)
    print(f"미등록 용어 목록 ({len(missing_list)}개)")
    print("="*40)
    
    # Print in columns or simple list
    for t in missing_list:
        print(t)
        
    print("="*40)
    print(f"완료. 총 {len(missing_list)}개의 용어가 용어집에 없습니다.")

if __name__ == "__main__":
    main()
