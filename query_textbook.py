import os
import sys
sys.path.append(r'c:\Users\gocom\Documents\Antigravity\Django_BaseCamp\03_1_model')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.conf import settings
from fileSearchStore import GeminiStoreManager

api_key = settings.GEMINI_API_KEY
manager = GeminiStoreManager(api_key=api_key)

target_store = '수목해충학'

manager.sync_all_stores()
    
prompt = '''1.3.3.1에 대한 내용 이해 문제를 5지선다형(문제번호	문제	보기1	보기2	보기3	보기4	보기5	정답	해설)으로 중복없이 최대한 출제하고 csv 형태로 만들어 주되 분리자는 tab으로 해'''

result = manager.query_store(target_store, prompt)

# 결과를 파일로 저장
with open('quiz_result.tsv', 'w', encoding='utf-8') as f:
    f.write(result)

print("결과가 quiz_result.tsv에 저장됨")
print(result)
