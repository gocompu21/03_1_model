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
    input_file = "physiology_explanations.json"
    
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
        
        # 일괄 업데이트를 위해 atomic 트랜잭션 사용 권장하지만, 
        # SQLite lock 최소화를 위해 단건 처리하거나 배치 사이즈 조절 가능.
        # 여기서는 속도를 위해 바로 진행.
        
        for idx, item in enumerate(data, 1):
            word = item.get('word')
            content = item.get('content')
            
            if not word or not content:
                continue
                
            try:
                # Term 조회 (ID가 아닌 단어 기준 - 로컬/서버 ID 불일치 방지)
                term = Term.objects.get(word=word)
                
                # 내용이 비어있거나 변경된 경우에만 업데이트
                if term.content != content:
                    term.content = content
                    term.save()
                    updated_count += 1
                    
                if idx % 100 == 0:
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
