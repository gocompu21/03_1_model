import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from exam.models import Question
from django.db.models import Q

def search_questions():
    keywords = ['동물', '가해', '청설모', '조류', '포유류', '설치류', '토끼', '사슴', '멧돼지']
    query = Q()
    for k in keywords:
        query.add(Q(content__icontains=k), Q.OR)
    
    questions = Question.objects.filter(query).select_related('exam', 'subject').order_by('exam__round_number', 'number')
    
    with open('animal_questions.txt', 'w', encoding='utf-8') as f:
        f.write(f'Total found: {questions.count()}\n')
        for q in questions:
            f.write(f'- [{q.exam.round_number}회 {q.subject.name}] {q.number}번: {q.content}\n')
    print("Results saved to animal_questions.txt")

if __name__ == '__main__':
    search_questions()
