import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import pandas as pd
from exam.models import Question

# 엑셀 파일 읽기
df = pd.read_excel('keywords_pathology.xlsx')
print(f"총 {len(df)}개 키워드 로드")

# 모든 Question 가져오기
questions = Question.objects.all()
print(f"총 {questions.count()}개 문제 검색")

# 각 키워드별로 문제/문항에서 검색
results = []
for idx, row in df.iterrows():
    keyword = row['용어']
    count = 0
    
    for q in questions:
        # 문제 지문에서 검색
        if keyword in (q.content or ''):
            count += 1
            continue
        # 선택지에서 검색
        choices = [q.choice1, q.choice2, q.choice3, q.choice4, q.choice5]
        if any(keyword in (c or '') for c in choices):
            count += 1
    
    results.append({
        '용어': keyword,
        '빈도수': count,
    })
    
    if (idx + 1) % 100 == 0:
        print(f"  {idx + 1}/{len(df)} 처리 중...")

# 결과를 DataFrame으로 변환
result_df = pd.DataFrame(results)

# 최대 빈도수 기준 %계산
max_count = result_df['빈도수'].max() if result_df['빈도수'].max() > 0 else 1
result_df['빈도율(%)'] = round((result_df['빈도수'] / max_count) * 100, 1)

# 빈도수 기준 내림차순 정렬
result_df = result_df.sort_values('빈도수', ascending=False)

# 저장
result_df.to_excel('keywords_pathology_updated.xlsx', index=False)
print(f"\n결과 저장: keywords_pathology_updated.xlsx")
print(f"빈도수 1 이상: {len(result_df[result_df['빈도수'] > 0])}개")
print("\n=== TOP 20 ===")
print(result_df.head(20).to_string(index=False))
