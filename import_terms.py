import os
import sys
import time
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import pandas as pd
from django.conf import settings
from glossary.models import Subject, Term

# fileSearchStore import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fileSearchStore import GeminiStoreManager

# 엑셀 파일 읽기
df = pd.read_excel('keywords_pathology_updated.xlsx')
# 빈도수 1 이상인 것만 필터링
df = df[df['빈도수'] >= 1]
print(f"처리할 키워드: {len(df)}개")

# 수목병리학 과목 가져오기
subject, _ = Subject.objects.get_or_create(name='수목병리학')
print(f"과목: {subject}")

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
created_count = 0
skipped_count = 0
error_count = 0

for idx, row in df.iterrows():
    keyword = row['용어']
    
    # 이미 존재하는지 확인
    if Term.objects.filter(word=keyword).exists():
        print(f"[{idx+1}/{len(df)}] 건너뜀 (이미 존재): {keyword}")
        skipped_count += 1
        continue
    
    try:
        # 기본서 조회
        prompt = f"{keyword}에 대해 설명해주세요."
        print(f"[{idx+1}/{len(df)}] 조회 중: {keyword}")
        
        raw_text = manager.query_store(target_store, prompt)
        
        if "No valid (ACTIVE) files found" in raw_text or "Store is empty" in raw_text:
            print(f"  -> 스토어 재동기화...")
            manager.sync_all_stores()
            raw_text = manager.query_store(target_store, prompt)
        
        # Term 저장
        term = Term.objects.create(
            word=keyword,
            content=raw_text
        )
        term.subjects.add(subject)
        created_count += 1
        print(f"  -> 저장 완료 (ID: {term.pk})")
        
    except Exception as e:
        print(f"  -> 오류: {e}")
        error_count += 1
    
    # API 할당량 초과 방지를 위한 대기
    print(f"  -> 20초 대기...")
    time.sleep(20)

print("=" * 50)
print(f"완료!")
print(f"  생성: {created_count}개")
print(f"  건너뜀: {skipped_count}개")
print(f"  오류: {error_count}개")
