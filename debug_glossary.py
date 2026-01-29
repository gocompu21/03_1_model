import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from glossary.models import Term, Subject
from exam.models import Question

# 1. 과목 확인
try:
    s = Subject.objects.get(name='수목해충학')
    print(f"Subject: {s.name} (ID: {s.id})")
except Subject.DoesNotExist:
    print("Subject '수목해충학' not found")
    exit()

# 2. 문제 확인
q_ids = set(Question.objects.filter(subject=s).values_list('id', flat=True))
print(f"Question IDs for {s.name}: {len(q_ids)} found")

# 3. 용어 및 레퍼런스 확인
terms = Term.objects.filter(subjects=s)[:5]
print(f"\nChecking first 5 terms:")

for term in terms:
    refs = list(term.references.all())
    q_refs = [r for r in refs if r.source_type == 'question']
    
    valid_refs = [r for r in q_refs if r.source_id in q_ids]
    
    print(f"- {term.word}: Total Refs {len(refs)}, Q Refs {len(q_refs)}, Valid Q Refs {len(valid_refs)}")
    if len(q_refs) > 0 and len(valid_refs) == 0:
        print(f"  WARNING: Has Question refs but none match subject {s.name}")
        # 샘플 확인
        r = q_refs[0]
        try:
            q = Question.objects.get(id=r.source_id)
            print(f"  Sample ref points to Q {q.id} (Subject: {q.subject.name}, ID: {q.subject.id})")
        except Question.DoesNotExist:
            print(f"  Sample ref points to non-existent Q {r.source_id}")

