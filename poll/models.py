"""AI 기초 설문 — 처음 수업을 듣는 분들의 AI 수준을 가늠한다.

로그인 없이 이름만 적고 답한다. 같은 이름으로 다시 내면 앞의 답을 덮어쓴다.
문항 보기는 여기 상수로 두고 화면·통계가 함께 쓴다.
"""

from django.db import models

AGE_CHOICES = [
    ("20", "20대 이하"),
    ("30", "30대"),
    ("40", "40대"),
    ("50", "50대"),
    ("60", "60대"),
    ("70", "70대 이상"),
]

DEVICE_CHOICES = [
    ("1", "전화·카톡 정도만"),
    ("2", "검색·쇼핑 가능"),
    ("3", "문서 작업 가능"),
    ("4", "업무에 능숙하게 사용"),
]

TOOL_CHOICES = [
    ("chatgpt", "ChatGPT"),
    ("gemini", "Gemini"),
    ("claude", "Claude"),
    ("naver", "네이버 클로바X·큐"),
    ("wrtn", "뤼튼"),
    ("copilot", "MS Copilot"),
    ("image", "이미지 AI (미드저니 등)"),
    ("none", "써 본 적 없음"),
]

FREQUENCY_CHOICES = [
    ("0", "써 본 적 없음"),
    ("1", "한두 번"),
    ("2", "한 달에 몇 번"),
    ("3", "일주일에 몇 번"),
    ("4", "거의 매일"),
]

USE_CHOICES = [
    ("ask", "궁금한 것 질문"),
    ("write", "글쓰기"),
    ("translate", "번역"),
    ("summary", "요약"),
    ("image", "이미지 만들기"),
    ("work", "업무 자료"),
    ("study", "공부"),
    ("code", "코딩"),
]

PAID_CHOICES = [
    ("no", "없음"),
    ("past", "써 봤지만 해지"),
    ("now", "현재 구독 중"),
]

TERMS = [
    ("genai", "생성형 AI"),
    ("prompt", "프롬프트"),
    ("hallucination", "할루시네이션(환각)"),
    ("llm", "LLM"),
    ("agent", "AI 에이전트"),
]

TERM_LEVELS = [
    ("0", "처음 들음"),
    ("1", "들어 봄"),
    ("2", "설명할 수 있음"),
]

# OX 문제: (키, 문장, 정답)
QUIZ = [
    ("q1", "AI의 답변은 항상 사실이다.", "X"),
    ("q2", "같은 질문을 해도 AI 답은 매번 조금씩 다를 수 있다.", "O"),
]

WORRY_CHOICES = [
    ("what", "무엇을 물어야 할지 모름"),
    ("trust", "답을 믿어도 되는지"),
    ("privacy", "개인정보"),
    ("signup", "가입·결제"),
    ("english", "영어"),
    ("none", "특별히 없음"),
]

SELF_LEVELS = [
    ("1", "1 전혀 모름"),
    ("2", "2"),
    ("3", "3 보통"),
    ("4", "4"),
    ("5", "5 능숙"),
]

# 수준 구간 (점수 0~100)
LEVELS = [
    (0, "입문"),
    (30, "초급"),
    (60, "중급"),
]


class PollResponse(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="이름")
    age_group = models.CharField(max_length=2, choices=AGE_CHOICES, verbose_name="연령대")
    device_level = models.CharField(max_length=1, choices=DEVICE_CHOICES, verbose_name="기기 활용")
    tools = models.JSONField(default=list, verbose_name="써 본 AI")
    frequency = models.CharField(max_length=1, choices=FREQUENCY_CHOICES, verbose_name="사용 빈도")
    uses = models.JSONField(default=list, blank=True, verbose_name="주로 하는 일")
    paid = models.CharField(max_length=4, choices=PAID_CHOICES, verbose_name="유료 구독")
    terms = models.JSONField(default=dict, verbose_name="용어 이해도")
    quiz = models.JSONField(default=dict, verbose_name="OX")
    self_level = models.CharField(max_length=1, choices=SELF_LEVELS, verbose_name="스스로 매긴 수준")
    worries = models.JSONField(default=list, blank=True, verbose_name="걱정되는 점")
    want_to_learn = models.TextField(blank=True, default="", verbose_name="배우고 싶은 것")
    score = models.IntegerField(default=0, verbose_name="수준 점수")
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="처음 제출")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="마지막 제출")

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "AI 설문 응답"
        verbose_name_plural = "AI 설문 응답"

    def __str__(self):
        return self.name

    def compute_score(self):
        """써 본 AI 수·빈도·용어·OX·자기평가를 합쳐 0~100으로."""
        tools = len([t for t in self.tools if t != "none"])
        points = min(tools, 3)                                   # 0~3
        points += int(self.frequency or 0)                       # 0~4
        points += sum(int(v) for v in self.terms.values())       # 0~10
        points += sum(1 for k, _, a in QUIZ if self.quiz.get(k) == a)  # 0~2
        points += int(self.self_level or 1) - 1                  # 0~4
        return round(points * 100 / 23)

    @property
    def level(self):
        label = LEVELS[0][1]
        for cut, name in LEVELS:
            if self.score >= cut:
                label = name
        return label
