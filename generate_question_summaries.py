"""
AI 기반 문제 요약 생성 스크립트
Gemini를 사용하여 각 문제의 summary 필드를 채웁니다.
"""
import os
import sys
import django
import time

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.conf import settings
from exam.models import Question
from google import genai

# Gemini 클라이언트 초기화
client = genai.Client(api_key=settings.GEMINI_API_KEY)

PROMPT_TEMPLATE = """다음 시험 문제를 10자 이내의 핵심 주제로 요약해주세요. 
조사나 불필요한 말 없이 핵심 용어만 포함하세요.

예시:
- "파이토플라스마의 설명 중 옳지 않은 것은?" → "파이토플라스마"
- "인공배양이 쉬우며 본래는 부생적으로 생활하는 것 이지만, 조건에 따라서는 기생생활을 할 수 있는 것은?" → "조건적 기생균"
- "밤나무 줄기마름병의 병원균에 대한 설명으로 옳지 않은 것은?" → "밤나무줄기마름병"

문제: {question}

선지:
① {choice1}
② {choice2}
③ {choice3}
④ {choice4}
⑤ {choice5}

핵심 주제(10자 이내):"""


def generate_summary(question):
    """Gemini를 사용하여 문제 요약 생성"""
    prompt = PROMPT_TEMPLATE.format(
        question=question.content,
        choice1=question.choice1,
        choice2=question.choice2,
        choice3=question.choice3,
        choice4=question.choice4,
        choice5=question.choice5
    )
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        summary = response.text.strip()
        # 10자 제한
        if len(summary) > 15:
            summary = summary[:15]
        return summary
    except Exception as e:
        print(f"Error generating summary: {e}")
        return None


def main():
    # 타겟 범위 설정 (기본: 모든 문제)
    round_number = None
    start_number = None
    end_number = None
    
    # 커맨드라인 인자 처리
    if len(sys.argv) >= 2:
        round_number = int(sys.argv[1])
    if len(sys.argv) >= 3:
        start_number = int(sys.argv[2])
    if len(sys.argv) >= 4:
        end_number = int(sys.argv[3])
    
    # 쿼리 빌드
    queryset = Question.objects.filter(summary__isnull=True) | Question.objects.filter(summary='')
    
    if round_number:
        queryset = queryset.filter(exam__round_number=round_number)
    if start_number:
        queryset = queryset.filter(number__gte=start_number)
    if end_number:
        queryset = queryset.filter(number__lte=end_number)
    
    queryset = queryset.order_by('exam__round_number', 'number')
    
    total = queryset.count()
    print(f"총 {total}개의 문제 요약 생성 예정")
    
    if total == 0:
        print("요약이 필요한 문제가 없습니다.")
        return
    
    for i, q in enumerate(queryset, 1):
        print(f"[{i}/{total}] {q.exam.round_number}회 {q.number}번... ", end="", flush=True)
        
        summary = generate_summary(q)
        if summary:
            q.summary = summary
            q.save(update_fields=['summary'])
            print(f"'{summary}'")
        else:
            print("FAILED")
        
        # Rate limit 방지
        time.sleep(0.3)
    
    print("\n완료!")


if __name__ == "__main__":
    main()
