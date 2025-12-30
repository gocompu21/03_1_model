"""
수목관리학 기출문제를 TXT 파일로 내보내기
"""
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from exam.models import Question

# Subject 매핑 확인 (1=수목생리학, 2=수목병리학, 3=수목해충학, 4=산림토양학, 5=수목관리학)
# 수목관리학 = 5번
questions = Question.objects.filter(subject=5).select_related('exam').order_by('exam__round_number', 'number')
print(f"수목관리학 문제 수: {questions.count()}개")

# TXT 파일 생성
output = []
output.append("=" * 60)
output.append("수목관리학 기출문제 모음")
output.append("나무의사 자격시험 5회~11회")
output.append(f"총 {questions.count()}문제")
output.append("=" * 60)
output.append("")

for q in questions:
    output.append(f"[{q.exam.round_number}회 {q.number}번]")
    output.append(f"문제: {q.content}")
    output.append("")
    output.append("보기:")
    output.append(f"① {q.choice1}")
    output.append(f"② {q.choice2}")
    output.append(f"③ {q.choice3}")
    output.append(f"④ {q.choice4}")
    output.append(f"⑤ {q.choice5}")
    output.append("")
    output.append(f"정답: {q.answer}번")
    output.append("")
    if q.textbook_chat:
        output.append("해설:")
        output.append(q.textbook_chat)
    output.append("")
    output.append("-" * 60)
    output.append("")

# 파일 저장
filename = "수목관리학_기출문제.txt"
with open(filename, "w", encoding="utf-8") as f:
    f.write("\n".join(output))

print(f"파일 저장 완료: {filename}")
