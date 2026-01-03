"""기출문제 텍스트 파일 생성 스크립트"""
import os
import sys
import django
import re

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from exam.models import Question

def clean_html(html):
    """HTML 태그 제거"""
    if not html:
        return ''
    text = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&amp;', '&')
    return text.strip()

def export_round(round_num):
    questions = Question.objects.filter(exam__round_number=round_num).order_by('number')
    
    if not questions.exists():
        print(f"⚠️ {round_num}회차 문제가 없습니다.")
        return
    
    output = []
    output.append("=" * 80)
    output.append(f"나무의사 제{round_num}회 기출문제 및 해설")
    output.append("=" * 80)
    output.append("")
    
    for q in questions:
        output.append("-" * 60)
        output.append(f"[{q.subject.name}] 문제 {q.number}번")
        output.append("-" * 60)
        output.append("")
        output.append(f"【문제】")
        output.append(clean_html(q.content))
        output.append("")
        output.append(f"① {clean_html(q.choice1)}")
        output.append(f"② {clean_html(q.choice2)}")
        output.append(f"③ {clean_html(q.choice3)}")
        output.append(f"④ {clean_html(q.choice4)}")
        output.append(f"⑤ {clean_html(q.choice5)}")
        output.append("")
        
        # 정답
        answer_map = {1: '①', 2: '②', 3: '③', 4: '④', 5: '⑤'}
        if isinstance(q.answer, list):
            answer_str = ', '.join([answer_map.get(a, str(a)) for a in q.answer])
        else:
            answer_str = answer_map.get(q.answer, str(q.answer))
        output.append(f"【정답】 {answer_str}")
        output.append("")
        
        # 해설 (기본서 해설 우선, 없으면 일반 해설)
        explanation = q.textbook_chat or q.general_chat or ''
        if explanation:
            output.append("【해설】")
            output.append(clean_html(explanation))
        else:
            output.append("【해설】 해설이 없습니다.")
        
        output.append("")
        output.append("")
    
    # 파일 저장
    filename = f"round{round_num}_questions_and_answers.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))
    
    print(f"✅ 파일 생성 완료: {filename} ({questions.count()}개 문제)")

def main():
    if len(sys.argv) > 1:
        rounds = [int(r) for r in sys.argv[1:]]
    else:
        rounds = [5]  # 기본값
    
    for round_num in rounds:
        export_round(round_num)

if __name__ == '__main__':
    main()
