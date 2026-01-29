
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
    input_file = "soil_explanations_existing.json"
    
    if not os.path.exists(input_file):
        print(f"❌ '{input_file}' not found.")
        return

    print(f"=== {input_file} 데이터 DB 병합 시작 ===")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        print(f"총 {len(data)}개 항목 로드됨.")
        
        updated_count = 0
        error_count = 0
        skipped_count = 0
        
        for idx, item in enumerate(data, 1):
            word = item.get('word')
            content = item.get('content')
            
            if not word or not content:
                continue
                
            try:
                term = Term.objects.get(word=word)
                
                # 병합 로직 (이미 내용이 있는 용어들임)
                final_content = content
                
                if term.content and term.content.strip():
                    if content.strip() in term.content:
                        skipped_count += 1
                        continue # 이미 포함됨
                    else:
                        # [산림토양학적 관점] 헤더 추가하여 병합
                        final_content = f"{term.content}\n\n<hr>\n\n### [산림토양학적 관점]\n\n{content}"
                
                if term.content != final_content:
                    term.content = final_content
                    term.save()
                    updated_count += 1
                    print(f"[{idx}] '{word}' 병합 완료")
                else:
                    skipped_count += 1
                    
            except Term.DoesNotExist:
                print(f"⚠️ Term '{word}' not found.")
                error_count += 1
            except Exception as e:
                print(f"⚠️ Error updating Term '{word}': {e}")
                error_count += 1
                
        print("=" * 30)
        print(f"완료. 업데이트: {updated_count}, 건너뜀: {skipped_count}, 오류: {error_count}")
        
    except Exception as e:
        print(f"❌ 치명적 오류: {e}")

if __name__ == "__main__":
    import_explanations()
