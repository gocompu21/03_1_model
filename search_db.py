import os
import sys
import django

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from exam.models import Question

def search_content():
    # Only search Round 6 as per hint, or all?
    # Term 5521 is CEC.
    # Text snippet: "30 cmol"
    print("Searching for '30 cmol'...")
    questions = Question.objects.filter(content__contains='30 cmol') | \
                Question.objects.filter(textbook_chat__contains='30 cmol') | \
                Question.objects.filter(general_chat__contains='30 cmol') | \
                Question.objects.filter(general_chat__contains='30 cmol') 

    for q in questions:
        print(f"Found in Q{q.id} (Round {q.exam.round_number} # {q.number})")
        
        if '30 cmol' in q.content:
            print("In Content")
        if q.textbook_chat and '30 cmol' in q.textbook_chat:
            print(f"In Chat: {q.textbook_chat[:100]}...")
            with open('debug_found_q.txt', 'w', encoding='utf-8') as f:
                f.write(q.textbook_chat)
        if q.general_chat and '30 cmol' in q.general_chat:
             print(f"In General: {q.general_chat[:100]}...")
             with open('debug_found_q.txt', 'w', encoding='utf-8') as f:
                f.write(q.general_chat)

search_content()
