
import os
import sys
import json
import django

# Django setup
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from glossary.models import Term

def import_explanations():
    input_file = "soil_explanations.json"
    
    if not os.path.exists(input_file):
        print(f"❌ '{input_file}' not found.")
        return

    print(f"=== {input_file} 데이터 DB 반영 시작 ===")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        print(f"총 {len(data)}개 항목 로드됨.")
        
        updated_count = 0
        error_count = 0
        
        for idx, item in enumerate(data, 1):
            word = item.get('word')
            content = item.get('content')
            
            if not word or not content:
                continue
                
            try:
                # Term 조회 (단어 기준)
                term = Term.objects.get(word=word)
                
                # 내용 업데이트 로직
                # 1. 기존 내용이 비어있으면 -> 그대로 저장
                # 2. 기존 내용이 있고, 현재 내용과 다르면 -> [산림토양학적 관점] 헤더 추가하여 병합
                
                final_content = content
                if term.content and term.content.strip():
                    # 이미 내용이 있는 경우 중복 체크
                    if content.strip() in term.content:
                        # 이미 포함된 내용이면 건너뜀 (또는 업데이트)
                        pass 
                    else:
                        # 기존 내용 뒤에 추가
                        final_content = f"{term.content}\n\n<hr>\n\n### [산림토양학적 관점]\n\n{content}"
                
                if term.content != final_content:
                    term.content = final_content
                    term.save()
                    updated_count += 1
                    
                if idx % 50 == 0:
                    print(f"[{idx}/{len(data)}] 처리 중...")
                    
            except Term.DoesNotExist:
                print(f"⚠️ Term '{word}' not found.")
                error_count += 1
            except Exception as e:
                print(f"⚠️ Error updating Term '{word}': {e}")
                error_count += 1
                
        print("=" * 30)
        print(f"완료. 업데이트: {updated_count}, 오류/실패: {error_count}")
        
    except Exception as e:
        print(f"❌ 치명적 오류: {e}")

if __name__ == "__main__":
    import_explanations()
