"""
기출문제에서 작용기작별 농약 정보를 분석하고 출제 빈도와 함께 정리하는 스크립트
"""
import os
import sys
import django
import re
from collections import Counter

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from exam.models import Question
import google.generativeai as genai


def analyze_pesticides_with_frequency():
    """기출문제에서 농약 정보 추출 및 출제 빈도 분석"""
    
    if not settings.GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY is not set")
        return
    
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    # 농약/살균제/살충제/제초제 관련 문제 수집
    keywords = ['농약', '살균제', '살충제', '제초제', '약제', '작용기작', '작용기전']
    
    all_questions = set()
    for kw in keywords:
        qs = Question.objects.filter(content__icontains=kw)
        for q in qs:
            all_questions.add(q.id)
        qs2 = Question.objects.filter(textbook_chat__icontains=kw)
        for q in qs2:
            all_questions.add(q.id)
    
    questions = Question.objects.filter(id__in=all_questions).select_related('exam').order_by('exam__round_number', 'number')
    
    print(f"총 {questions.count()}개 농약 관련 문제 발견")
    print("="*80)
    
    # 모든 관련 문제와 해설 수집
    question_data = []
    all_text = ""
    
    for q in questions:
        text = f"{q.content} {q.choice1} {q.choice2} {q.choice3} {q.choice4} {q.choice5} {q.textbook_chat if q.textbook_chat else ''}"
        all_text += text + "\n"
        
        data = f"""
[{q.exam.round_number}회 {q.number}번]
문제: {q.content}
보기: ① {q.choice1} ② {q.choice2} ③ {q.choice3} ④ {q.choice4} ⑤ {q.choice5}
정답: {q.answer}번
해설: {q.textbook_chat if q.textbook_chat else '(없음)'}
"""
        question_data.append(data)
    
    # 1단계: 먼저 농약 목록 추출
    print("1단계: 농약 목록 추출 중...")
    
    extract_prompt = f"""다음은 나무의사 자격시험 기출문제들의 전체 텍스트입니다. 
이 텍스트에서 언급된 모든 농약/약제 이름을 추출해주세요.

{all_text[:50000]}

## 요청:
1. 위 텍스트에서 언급된 모든 농약/약제 이름을 한 줄에 하나씩 나열해주세요.
2. 중복은 제거하되, 영문명과 한글명이 다르면 모두 포함하세요.
3. 작용기작명은 제외하고 약제명만 추출하세요.
4. 다음 형식으로만 출력하세요 (다른 설명 없이):

약제명1
약제명2
약제명3
...
"""
    
    try:
        response = model.generate_content(extract_prompt)
        pesticide_list = response.text.strip().split('\n')
        pesticide_list = [p.strip() for p in pesticide_list if p.strip() and len(p.strip()) > 1]
        print(f"  추출된 농약 수: {len(pesticide_list)}개")
    except Exception as e:
        print(f"Error extracting pesticides: {e}")
        return
    
    # 2단계: 각 농약의 출제 빈도 계산
    print("\n2단계: 출제 빈도 계산 중...")
    
    frequency_counter = Counter()
    
    for pesticide in pesticide_list:
        count = 0
        for q in questions:
            text = f"{q.content} {q.choice1} {q.choice2} {q.choice3} {q.choice4} {q.choice5}"
            if pesticide.lower() in text.lower():
                count += 1
        if count > 0:
            frequency_counter[pesticide] = count
    
    print(f"  빈도 계산 완료: {len(frequency_counter)}개 약제")
    
    # 3단계: 작용기작별 분류 (빈도 정보 포함)
    print("\n3단계: 작용기작별 분류 중...")
    
    # 빈도 정보를 포함한 텍스트 생성
    freq_text = "\n".join([f"- {name}: {count}회 출제" for name, count in frequency_counter.most_common()])
    
    chunk_text = "\n".join(question_data[:40])  # 처음 40문제만 사용
    
    classify_prompt = f"""다음은 나무의사 자격시험 기출문제들과 각 농약의 출제 빈도입니다.

## 출제 빈도 (높은 순):
{freq_text}

## 기출문제 샘플:
{chunk_text[:30000]}

## 분석 요청:
위 정보를 바탕으로 **작용기작별로 농약을 분류**하고, 각 농약 옆에 출제 빈도를 표시해주세요.

다음 형식으로 정리해주세요:

# 살균제

## [작용기작명] (예: 세포막 스테롤 생합성 저해)
| 약제명 | 출제 빈도 | 비고 |
|--------|-----------|------|
| **디페노코나졸** | 5회 | 트리아졸계 |

# 살충제

## [작용기작명]
| 약제명 | 출제 빈도 | 비고 |
|--------|-----------|------|
| **이미다클로프리드** | 8회 | 네오니코티노이드계 |

# 제초제

## [작용기작명]
| 약제명 | 출제 빈도 | 비고 |
|--------|-----------|------|
| **글리포세이트** | 6회 | EPSPS 저해 |

주의사항:
1. 출제 빈도가 높은 약제(3회 이상)는 **굵게** 표시
2. 출제 빈도 순으로 정렬
3. 마크다운 테이블 형식 사용
"""
    
    try:
        response = model.generate_content(classify_prompt)
        result = response.text
        print(result)
        
        # 파일로 저장
        with open("pesticide_analysis_with_frequency.md", "w", encoding="utf-8") as f:
            f.write("# 나무의사 시험 기출문제 - 작용기작별 농약 정리 (출제 빈도 포함)\n\n")
            f.write(f"분석 대상: {questions.count()}개 문제\n\n")
            f.write("---\n\n")
            f.write("## 📊 출제 빈도 TOP 20\n\n")
            f.write("| 순위 | 약제명 | 출제 횟수 |\n")
            f.write("|------|--------|----------|\n")
            for i, (name, count) in enumerate(frequency_counter.most_common(20), 1):
                f.write(f"| {i} | **{name}** | {count}회 |\n")
            f.write("\n---\n\n")
            f.write(result)
        
        print("\n" + "="*80)
        print("결과가 pesticide_analysis_with_frequency.md에 저장되었습니다.")
        
    except Exception as e:
        print(f"Classification error: {e}")


if __name__ == "__main__":
    analyze_pesticides_with_frequency()
