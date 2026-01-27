import os
import django
import pandas as pd
import sys

# Django Setup
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from glossary.models import Term, Subject

def import_terms():
    file_path = 'data/수목생리학_용어정리.xlsx'
    df = pd.read_excel(file_path)
    
    # 1. Subject 가져오기/생성
    subject_name = "수목생리학"
    subject, created = Subject.objects.get_or_create(name=subject_name)
    if created:
        print(f"Created Subject: {subject_name}")
    else:
        print(f"Found Subject: {subject_name}")
        
    created_count = 0
    updated_count = 0
    
    for index, row in df.iterrows():
        term_word = str(row['용어']).strip()
        page_info = str(row['페이지']).strip() if '페이지' in row and not pd.isna(row['페이지']) else ""
        
        if not term_word:
            continue
            
        # 2. Term 가져오기/생성
        term, created = Term.objects.get_or_create(word=term_word, defaults={'content': ''})
        
        # 3. Page 정보 추가 (이미 내용이 있으면 추가하지 않거나, 따로 처리)
        # 여기서는 내용이 비어있으면 "페이지: ..." 형식으로 임시 저장하거나 비워둠.
        # 사용자가 "용어집"이라고 했으므로 정의가 중요함. 정의는 추후 생성한다고 가정.
        # page 정보는 일단 content가 비어있을 때만 넣거나, 나중에 AI가 덮어쓸 수 있음.
        # 전략: content가 비어있으면 비워둠. 페이지 정보는 로그로만 남김 (모델에 page 필드가 없음).
        # 혹시 content에 페이지 정보를 남기고 싶다면:
        # if not term.content and page_info:
        #     term.content = f"(참고 페이지: {page_info})"
        #     term.save()
        
        # 4. Subject 연결
        if subject not in term.subjects.all():
            term.subjects.add(subject)
            if not created:
                updated_count += 1
        
        if created:
            created_count += 1
            print(f"Created: {term_word}")
        
    print(f"Finished. Created: {created_count}, Updated(added subject): {updated_count}")

if __name__ == "__main__":
    import_terms()
