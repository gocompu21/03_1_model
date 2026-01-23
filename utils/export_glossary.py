import os
import sys
import django
import json

# Django Setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from glossary.models import Term, Subject

def export_glossary():
    # 수목해충학 과목 가져오기
    try:
        subject = Subject.objects.get(name__contains='수목해충학')
    except Subject.DoesNotExist:
        print("수목해충학 과목이 없습니다.")
        return

    terms = Term.objects.filter(subjects=subject)
    print(f"추출 대상 용어: {terms.count()}개")
    
    data = []
    for term in terms:
        item = {
            'word': term.word,
            'content': term.content,
            'subjects': [s.name for s in term.subjects.all()]
        }
        data.append(item)
    
    filename = 'glossary_entomology_data.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"저장 완료: {filename} ({len(data)}건)")

if __name__ == "__main__":
    export_glossary()
