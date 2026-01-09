import os
import sys
import time
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from glossary.models import Subject, Term

# fileSearchStore import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fileSearchStore import GeminiStoreManager

# 67자 = 오류 메시지인 용어들 찾기
error_terms = [t for t in Term.objects.all() if len(t.content or '') == 67]
print(f"재조회 대상 용어: {len(error_terms)}개")

if not error_terms:
    print("재조회할 용어가 없습니다.")
    exit()

# 수목병리학 과목 가져오기
subject = Subject.objects.get(name='수목병리학')

# GeminiStoreManager 초기화
api_key = settings.GEMINI_API_KEY
manager = GeminiStoreManager(api_key=api_key)

# 타겟 스토어
target_store = "수목병리학"
if target_store not in manager.stores or not manager.stores[target_store]:
    print(f"스토어 동기화 중...")
    manager.sync_all_stores()

print(f"스토어 준비 완료: {target_store}")
print("=" * 50)

# 처리 카운트
success_count = 0
error_count = 0

for idx, term in enumerate(error_terms):
    try:
        prompt = f"{term.word}에 대해 설명해주세요."
        print(f"[{idx+1}/{len(error_terms)}] 재조회 중: {term.word}")
        
        raw_text = manager.query_store(target_store, prompt)
        
        # 오류 응답이 아닌 경우에만 업데이트
        if "429" not in raw_text and "Error" not in raw_text and len(raw_text) > 100:
            term.content = raw_text
            term.save()
            success_count += 1
            print(f"  -> 업데이트 완료 ({len(raw_text)}자)")
        else:
            error_count += 1
            print(f"  -> 여전히 오류: {raw_text[:50]}...")
        
    except Exception as e:
        print(f"  -> 예외: {e}")
        error_count += 1
    
    # API 할당량 초과 방지를 위한 대기
    print(f"  -> 60초 대기...")
    time.sleep(60)

print("=" * 50)
print(f"완료!")
print(f"  성공: {success_count}개")
print(f"  실패: {error_count}개")
