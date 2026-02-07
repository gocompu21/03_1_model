"""
과목별 기출문제를 Markdown 파일로 내보내기
사용법: python export_subject_questions.py
"""
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from exam.models import Question

# ===== 설정 =====
SUBJECT_NAME = "수목해충학"
ROUNDS = range(5, 12)  # 5~11회
# ================


def circle_number(n):
    return {1: "①", 2: "②", 3: "③", 4: "④", 5: "⑤"}.get(n, str(n))


questions = (
    Question.objects.filter(subject__name=SUBJECT_NAME, exam__round_number__in=ROUNDS)
    .select_related("exam")
    .order_by("exam__round_number", "number")
)
print(f"{SUBJECT_NAME} 문제 수: {questions.count()}개")

output = []
output.append(f"# {SUBJECT_NAME} 기출문제 ({ROUNDS[0]}~{ROUNDS[-1]}회)\n")

current_round = None
for q in questions:
    if q.exam.round_number != current_round:
        current_round = q.exam.round_number
        output.append(f"\n---\n\n## {current_round}회\n")

    output.append(f"### {q.number}번")
    output.append(f"{q.content}\n")
    output.append(f"① {q.choice1}")
    output.append(f"② {q.choice2}")
    output.append(f"③ {q.choice3}")
    output.append(f"④ {q.choice4}")
    output.append(f"⑤ {q.choice5}\n")

    answer_str = ", ".join(circle_number(a) for a in q.answer)
    output.append(f"**정답:** {answer_str}\n")

    explanation = q.textbook_chat or q.general_chat or ""
    if explanation.strip():
        output.append(f"**해설:**\n{explanation.strip()}\n")

    output.append("")

filename = f"{SUBJECT_NAME}_기출문제_{ROUNDS[0]}-{ROUNDS[-1]}회.md"
with open(filename, "w", encoding="utf-8") as f:
    f.write("\n".join(output))

size_kb = os.path.getsize(filename) / 1024
print(f"파일 저장 완료: {filename} ({size_kb:.1f} KB)")
