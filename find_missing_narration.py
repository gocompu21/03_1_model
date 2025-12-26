import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from exam.models import Question, Exam

exam = Exam.objects.get(round_number=5)
questions = Question.objects.filter(exam=exam).order_by("number")

# 나레이션이 없는 문제 찾기
missing_narration = []
for q in questions:
    if not q.narration or not q.narration.strip():
        missing_narration.append(q.number)
        print(f"문제 {q.number}번: 나레이션 없음")
        print(f"  - textbook_chat 있음: {bool(q.textbook_chat)}")
        if q.textbook_chat:
            print(f"  - textbook_chat 길이: {len(q.textbook_chat)} chars")

if not missing_narration:
    print("모든 문제에 나레이션이 있습니다!")
else:
    print(f"\n총 {len(missing_narration)}개 문제에 나레이션이 없습니다: {missing_narration}")
