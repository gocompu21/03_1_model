import os
import json
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from glossary.models import Term, Subject, TermReference

# Convert datetime to string for references
refs = []
for r in TermReference.objects.all():
    refs.append({
        'id': r.id,
        'term_id': r.term_id,
        'source_type': r.source_type,
        'source_id': r.source_id,
        'source_title': r.source_title if hasattr(r, 'source_title') else '',
        'created_at': str(r.created_at)
    })

data = {
    'terms': [],
    'subjects': list(Subject.objects.values('id', 'name')),
    'term_subjects': [],
    'references': refs
}

for t in Term.objects.all():
    data['terms'].append({
        'id': t.id,
        'word': t.word,
        'content': t.content,
        'created_at': str(t.created_at),
        'updated_at': str(t.updated_at)
    })
    data['term_subjects'].append({
        'term_id': t.id,
        'subject_ids': [s.id for s in t.subjects.all()]
    })

with open('glossary_export_0110.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Exported: {len(data['terms'])} terms, {len(data['references'])} refs")
