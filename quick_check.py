import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import Chapter, PracticeQuestion

chapter = Chapter.objects.filter(code='2.3.1').first()
if chapter:
    questions = PracticeQuestion.objects.filter(chapter=chapter).order_by('number')
    
    for q in questions:
        exp_len = len(q.explanation) if q.explanation else 0
        has_good_exp = exp_len > 200  # Good explanations are usually > 200 chars
        status = '✓' if has_good_exp else '✗'
        print(f'{status} Q{q.number} (ID:{q.id}): {exp_len} chars')
