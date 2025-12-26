import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from exam.models import Question

questions = Question.objects.filter(exam__round_number__in=[5,6,7,8,9,10,11])
total = questions.count()
with_narration = questions.exclude(narration='').exclude(narration__isnull=True).count()

print(f'전체: {total}문제')
print(f'나레이션 있음: {with_narration}문제')
print(f'진행률: {with_narration}/{total} ({with_narration*100//total if total > 0 else 0}%)')

# 회차별 통계
for round_num in range(5, 12):
    round_qs = questions.filter(exam__round_number=round_num)
    round_total = round_qs.count()
    round_with = round_qs.exclude(narration='').exclude(narration__isnull=True).count()
    print(f'{round_num}회: {round_with}/{round_total}')
