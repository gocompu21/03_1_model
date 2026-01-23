import os
import sys
import django
import json

# Django Setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from glossary.models import Term, Subject

def import_glossary():
    filename = 'glossary_entomology_data.json'
    
    if not os.path.exists(filename):
        print(f"파일을 찾을 수 없습니다: {filename}")
        return

    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"가져올 데이터: {len(data)}건")
    
    created_count = 0
    updated_count = 0
    
    for item in data:
        word = item['word']
        content = item['content']
        subject_names = item['subjects']
        
        # Term 생성 또는 조회
        term, created = Term.objects.get_or_create(word=word)
        
        if created:
            term.content = content
            term.save()
            created_count += 1
        else:
            # 기존 내용이 비어있으면 채워넣기 (선택 사항)
            if not term.content and content:
                term.content = content
                term.save()
                updated_count += 1
        
        # 과목 연결
        for s_name in subject_names:
            subject, _ = Subject.objects.get_or_create(name=s_name)
            term.subjects.add(subject)
            
    print(f"완료!")
    print(f"  신규 생성: {created_count}개")
    print(f"  업데이트: {updated_count}개")

if __name__ == "__main__":
    import_glossary()
