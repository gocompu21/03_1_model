import os
import re
import json
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from exam.models import Question, Subject
from collections import Counter

# 수목병리학 과목 찾기
pathology_subject = Subject.objects.filter(name__icontains='병리').first()
print(f'과목: {pathology_subject}')

# 키워드 추출 패턴
bold_patterns = [
    r'<strong>([^<]+)</strong>',
    r'<b>([^<]+)</b>',
    r'\*\*([^*]+)\*\*',
]
italic_patterns = [
    r'<i>([^<]+)</i>',
    r'<em>([^<]+)</em>',
]

# 노이즈 필터링
noise_words = [
    '선지별', '정답', '옳음', '틀림', '옳지', '해설', '분석', '설명', 
    '이유', '결론', '문제', '핵심', '요약', '정리', '내용', '답변',
    '보기', '선지', '①', '②', '③', '④', '⑤', '번호',
]

keywords = []
questions = Question.objects.filter(subject=pathology_subject)
print(f'수목병리학 문제 수: {questions.count()}')

for q in questions:
    texts = [q.content, q.choice1, q.choice2, q.choice3, q.choice4, q.choice5]
    if q.textbook_chat:
        texts.append(q.textbook_chat)
    if q.general_chat:
        texts.append(q.general_chat)
    
    for text in texts:
        if not text:
            continue
        for pattern in bold_patterns + italic_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            keywords.extend(matches)

# 정리 및 필터링
clean_keywords = []
for k in keywords:
    k = k.strip()
    # 길이 체크
    if len(k) < 2 or len(k) > 50:
        continue
    # 노이즈 단어 포함 여부
    if any(noise in k for noise in noise_words):
        continue
    # 숫자만 있는 경우 제외
    if k.replace('.', '').replace(':', '').isdigit():
        continue
    clean_keywords.append(k)

counter = Counter(clean_keywords)
max_count = counter.most_common(1)[0][1] if counter else 1

# JSON 형식으로 저장
result = {
    'subject': '수목병리학',
    'total_keywords': len(counter),
    'total_questions': questions.count(),
    'keywords': []
}

for word, count in counter.most_common():
    percentage = round((count / max_count) * 100, 1)
    result['keywords'].append({
        'word': word,
        'count': count,
        'frequency_percent': percentage
    })

with open('keywords_pathology.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"Total {len(counter)} keywords saved to: keywords_pathology.json")
print("\n=== TOP 20 Keywords ===")
for item in result['keywords'][:20]:
    print(f"{item['frequency_percent']:5.1f}%  ({item['count']:2d}x) {item['word']}")
