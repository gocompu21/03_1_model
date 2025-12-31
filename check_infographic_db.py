"""Check and display infographic_image field values for specific questions."""
import os
import sys
import django

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from exam.models import Question

questions_to_check = [
    (5, 52),
    (5, 124),
    (6, 94),
]

print("=== 인포그래픽 이미지 DB 확인 ===")
for round_num, q_num in questions_to_check:
    q = Question.objects.filter(exam__round_number=round_num, number=q_num).first()
    if q:
        img_name = q.infographic_image.name if q.infographic_image else "None"
        print(f"{round_num}회 {q_num}번 (ID={q.id}): {img_name}")
    else:
        print(f"{round_num}회 {q_num}번: 문제를 찾을 수 없음")
