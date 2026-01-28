"""
NotebookLM 용어 설명 DB Import 스크립트
notebooklm_explanations.json 파일의 내용을 DB에 반영합니다.

EC2에서 실행:
    git pull
    python import_notebooklm_explanations.py
"""
import os
import sys
import json
import django

# Django setup
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from glossary.models import Term

def main():
    input_file = "notebooklm_explanations.json"
    
    print(f"=== NotebookLM 용어 설명 DB Import ===")
    print(f"입력 파일: {input_file}")
    
    # JSON 파일 로드
    if not os.path.exists(input_file):
        print(f"❌ 파일을 찾을 수 없습니다: {input_file}")
        return
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📂 {len(data)}개 항목 로드됨")
    
    updated_count = 0
    skipped_count = 0
    not_found_count = 0
    
    for item in data:
        word = item.get('word')
        content = item.get('content')
        
        if not word or not content:
            skipped_count += 1
            continue
        
        try:
            term = Term.objects.get(word=word)
            
            # 내용이 비어있거나 변경된 경우에만 업데이트
            if term.content != content:
                term.content = content
                term.save()
                updated_count += 1
                print(f"✅ 업데이트: {word}")
            else:
                skipped_count += 1
                
        except Term.DoesNotExist:
            not_found_count += 1
            print(f"⚠️ 용어 없음: {word}")
        except Term.MultipleObjectsReturned:
            # 동일 단어가 여러 개인 경우 첫 번째만 업데이트
            term = Term.objects.filter(word=word).first()
            if term and term.content != content:
                term.content = content
                term.save()
                updated_count += 1
                print(f"✅ 업데이트 (첫 번째): {word}")
    
    print("=" * 50)
    print(f"완료!")
    print(f"  - 업데이트: {updated_count}개")
    print(f"  - 건너뜀 (변경없음): {skipped_count}개")
    print(f"  - 용어 없음: {not_found_count}개")

if __name__ == "__main__":
    main()
