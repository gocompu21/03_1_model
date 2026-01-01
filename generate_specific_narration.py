"""Generate narration for specific questions."""
import os
import sys
import time
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from exam.models import Question
import google.generativeai as genai

NARRATION_PROMPT = """당신은 나무의사 자격 시험을 준비하는 수험생을 위한 전문 강사입니다.

다음 문제와 해설을 바탕으로, 음성으로 들려줄 전문적이고 명확한 나레이션을 작성해주세요.

[요구사항]
1. 맨 앞에 인사나 다른 말을 하지 말고, 문제를 읽지 말고 바로 정답 해설로 시작하세요.
2. 마지막에 "수험생 여러분" 등의 감사 인사를 하지 말고 깔끔하게 설명으로 끝내세요.
3. 전문 용어는 쉽게 풀어서 설명해주세요.
4. 중요한 포인트는 **굵게** 표시하여 강조해주세요.
5. 자연스럽게 읽을 수 있는 문장으로 작성해주세요.
6. LaTeX 수식이나 특수 기호는 읽을 수 있는 텍스트로 변환해주세요.
7. 마크다운 형식(**, *, - 등)을 활용하여 가독성을 높여주세요.

[문제]
{question_content}

[보기]
① {choice1}
② {choice2}
③ {choice3}
④ {choice4}
⑤ {choice5}

[정답]
{answer}번

[기본서 해설]
{textbook_chat}

위 내용을 바탕으로 전문적이고 명확한 나레이션을 마크다운 형식으로 작성해주세요."""


def main():
    # Specific questions to generate
    questions_to_generate = [
        (11, 8),
        (11, 99),
    ]
    
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    print("=== 특정 문제 나레이션 생성 ===")
    print(f"대상: {questions_to_generate}")
    
    success = 0
    fail = 0
    
    for round_num, q_num in questions_to_generate:
        print(f"\n{round_num}회 {q_num}번 처리 중...", end=" ")
        
        q = Question.objects.filter(exam__round_number=round_num, number=q_num).first()
        if not q:
            print("❌ 문제 없음")
            fail += 1
            continue
        
        if not q.textbook_chat or not q.textbook_chat.strip():
            print("❌ textbook_chat 없음")
            fail += 1
            continue
        
        try:
            prompt = NARRATION_PROMPT.format(
                question_content=q.content,
                choice1=q.choice1,
                choice2=q.choice2,
                choice3=q.choice3,
                choice4=q.choice4,
                choice5=q.choice5,
                answer=q.answer,
                textbook_chat=q.textbook_chat
            )
            
            response = model.generate_content(prompt)
            narration_text = response.text
            
            q.narration = narration_text
            q.save()
            
            print(f"✅ {len(narration_text)} chars")
            success += 1
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ 오류: {e}")
            fail += 1
    
    print(f"\n완료! 성공: {success}, 실패: {fail}")


if __name__ == "__main__":
    main()
