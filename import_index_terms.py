import os
import django
import pandas as pd

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from glossary.models import Term, Subject

def import_terms():
    file_path = 'pathology_index.xlsx'
    if not os.path.exists(file_path):
        print("엑셀 파일이 없습니다.")
        return

    df = pd.read_excel(file_path)
    
    # 수목병리학 과목 가져오기/생성
    subject, _ = Subject.objects.get_or_create(name='수목병리학')
    
    existing_words = set(Term.objects.values_list('word', flat=True))
    
    added_count = 0
    passed_count = 0
    
    for idx, row in df.iterrows():
        word = str(row['Term']).strip()
        
        if not word:
            continue
            
        if word in existing_words:
            passed_count += 1
            # 이미 존재하면 패스 (과목 추가는 선택사항이지만 일단 패스)
            # 만약 과목 연결이 필요하면 여기서 term.subjects.add(subject)
            term = Term.objects.get(word=word)
            if not term.subjects.filter(id=subject.id).exists():
                 term.subjects.add(subject)
            continue
            
        # 새 용어 생성
        term = Term.objects.create(
            word=word,
            content="" # 내용은 나중에 채움
        )
        term.subjects.add(subject)
        existing_words.add(word) # 중복 방지 업데이트
        added_count += 1
        
    print(f"완료: {added_count}개 추가, {passed_count}개 패스")

if __name__ == '__main__':
    import_terms()
