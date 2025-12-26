import os
import sys
import time
import django

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from exam.models import Question, Exam
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


def generate_narration_for_round(round_number):
    """Generate narration for all questions in a specific exam round."""
    
    if not settings.GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY is not set")
        return
    
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    try:
        exam = Exam.objects.get(round_number=round_number)
    except Exam.DoesNotExist:
        print(f"Exam round {round_number} not found")
        return
    
    questions = Question.objects.filter(exam=exam).order_by("number")
    total = questions.count()
    
    print(f"Processing {total} questions for Exam {round_number}회...")
    
    generated = 0
    skipped = 0
    errors = 0
    
    for i, q in enumerate(questions):
        print(f"\n[{i+1}/{total}] Question {q.number}번")
        
        # Skip if no textbook_chat
        if not q.textbook_chat or not q.textbook_chat.strip():
            print("  Skipped (no textbook_chat)")
            skipped += 1
            continue
        
        # Build prompt
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
        
        try:
            response = model.generate_content(prompt)
            narration_text = response.text
            
            # Save to database
            q.narration = narration_text
            q.save()
            
            print(f"  Generated: {len(narration_text)} chars")
            generated += 1
            
            # Rate limiting
            time.sleep(2)
            
        except Exception as e:
            print(f"  Error: {str(e)}")
            errors += 1
            
            # If rate limited, wait longer
            if "429" in str(e) or "quota" in str(e).lower():
                print("  Rate limited. Waiting 60 seconds...")
                time.sleep(60)
    
    print(f"\n{'='*50}")
    print("Completed!")
    print(f"  Generated: {generated}")
    print(f"  Skipped: {skipped}")
    print(f"  Errors: {errors}")


if __name__ == "__main__":
    # Generate narration for Exam Round 5
    generate_narration_for_round(5)
