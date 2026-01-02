import os, sys, django, re
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from exam.models import Question

def clean_html(html):
    if not html: return ''
    text = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&nbsp;', ' ').strip()
    return text

q = Question.objects.filter(exam__round_number=5, number=27).first()
if q:
    subject = q.subject.name
    content = clean_html(q.content)
    c1 = clean_html(q.choice1)
    c2 = clean_html(q.choice2)
    c3 = clean_html(q.choice3)
    c4 = clean_html(q.choice4)
    c5 = clean_html(q.choice5)
    expl = q.textbook_chat or q.general_chat or ''
    print(f'''({subject}) 5-27. {content}
① {c1}
② {c2}
③ {c3}
④ {c4}
⑤ {c5}

{expl[:800]}...

위 내용으로 인포그래픽을 만들어 줘
요구사항：
１） １６：９ 비율
２） 한국어 텍스트 포함
３） 전문적이고 교육적인 스타일
４） 나무 병해 관련 시각 요소
５） 최상단칸은 "({subject}) 5-27. {content}" 왼쪽 정렬해''')
else:
    print('Question not found')
