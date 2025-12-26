import os
import sys
import django

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

genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

exam = Exam.objects.get(round_number=5)
q = Question.objects.filter(exam=exam, number=104).first()

print(f"5회 104번 문제 나레이션 생성 중...")

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
    q.narration = response.text
    q.save()
    print(f"✓ 성공! 생성된 나레이션 길이: {len(response.text)} chars")
    print(f"\n처음 200자:\n{response.text[:200]}")
except Exception as e:
    print(f"✗ 에러 발생: {e}")
