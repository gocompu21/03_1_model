import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from glossary.models import Term, TermReference
from exam.models import Question

try:
    term = Term.objects.get(word='Sphaeropsis sapinea')
    print(f"용어: {term.word}")
    
    refs = TermReference.objects.filter(term=term)
    if not refs.exists():
        print("연결된 문제가 없습니다.")
    
    for r in refs:
        try:
            q = Question.objects.get(pk=r.source_id)
            print(f"\n[링크] {r.source_title} (ID: {q.id})")
            print(f"과목: {q.subject.name}")
            print(f"문제: {q.content}")
            print(f"보기1: {q.choice1}")
            print(f"보기2: {q.choice2}")
            print(f"보기3: {q.choice3}")
            print(f"보기4: {q.choice4}")
            print(f"보기5: {q.choice5}")
            
            # 검색어가 어디에 있는지 확인
            search_texts = {
                '문제': q.content,
                '보기1': q.choice1,
                '보기2': q.choice2,
                '보기3': q.choice3,
                '보기4': q.choice4,
                '보기5': q.choice5,
                '일반해설': q.general_chat,
                '기본서해설': q.textbook_chat,
            }
            
            found_in = []
            for where, text in search_texts.items():
                if text and term.word in text:
                    found_in.append(where)
            
            if found_in:
                print(f"-> '{term.word}' 발견 위치: {', '.join(found_in)}")
                for where in found_in:
                    print(f"   [{where}] ...{term.word}...")
            else:
                print(f"-> '{term.word}'가 텍스트에서 발견되지 않았습니다. (부분 일치나 대소문자 문제일 수 있음)")
                
        except Question.DoesNotExist:
            print(f"문제 ID {r.source_id}를 찾을 수 없습니다.")

except Term.DoesNotExist:
    print(f"용어 'Sphaeropsis sapinea'를 찾을 수 없습니다.")
