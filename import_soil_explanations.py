
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
                
                # 내용이 비어있거나 변경된 경우에만 업데이트
                # (기존 내용이 있어도 덮어쓰기 원하면 조건문 제거)
                # 여기서는 '비어있거나' 조건만 체크하는 게 안전할 수 있으나,
                # batch_fill 스크립트 자체가 빈 것만 찾았으므로 그냥 덮어써도 무방함.
                if term.content != content:
                    term.content = content
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
