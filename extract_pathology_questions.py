"""
수목병리학 5~11회 전체 기출문제를 JSON으로 추출.
EC2에서 실행: python extract_pathology_questions.py
"""
import os, sys, json, django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from exam.models import Question, Subject

subject = Subject.objects.get(name__contains="수목병리")
print(f"과목: {subject.name} (pk={subject.pk})")

questions = Question.objects.filter(
    subject=subject,
    exam__round_number__gte=5,
    exam__round_number__lte=11,
).select_related("exam").order_by("exam__round_number", "number")

data = []
for q in questions:
    data.append({
        "round": q.exam.round_number,
        "number": q.number,
        "ref": f"{q.exam.round_number}-{q.number}",
        "content": q.content,
        "choice1": q.choice1,
        "choice2": q.choice2,
        "choice3": q.choice3,
        "choice4": q.choice4,
        "choice5": q.choice5,
        "answer": q.answer,
        "explanation": q.general_chat or "",
    })

out_path = os.path.join(os.path.dirname(__file__), "pathology_questions.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"추출 완료: {len(data)}문제 → {out_path}")
# 회차별 문제 수 출력
from collections import Counter
rc = Counter(q["round"] for q in data)
for r in sorted(rc):
    print(f"  {r}회: {rc[r]}문제")
