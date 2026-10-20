from django.db import models

# 보기 목록 — 설문 화면과 통계 화면이 함께 쓴다
SKILL_CHOICES = [
    ("call", "전화·카톡 정도만"),
    ("search", "검색·쇼핑 가능"),
    ("docs", "문서 작업 가능"),
    ("work", "업무에 능숙하게 사용"),
]

AI_TOOL_CHOICES = [
    ("chatgpt", "ChatGPT"),
    ("gemini", "Gemini"),
    ("claude", "Claude"),
    ("naver", "네이버 클로바X·큐"),
    ("wrtn", "뤼튼"),
    ("copilot", "MS Copilot"),
    ("image", "이미지 AI(미드저니 등)"),
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
    ("coding", "코딩"),
]

SUBSCRIPTION_CHOICES = [
    ("none", "없음"),
    ("cancelled", "써 봤지만 해지"),
    ("active", "현재 구독 중"),
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

# (키, 문장, 정답)
OX_QUESTIONS = [
    ("q1", "AI의 답변은 항상 사실이다.", "X"),
    ("q2", "같은 질문을 해도 AI 답은 매번 조금씩 다를 수 있다.", "O"),
]

SELF_LEVEL_CHOICES = [
    ("1", "1 전혀 모름"),
    ("2", "2"),
    ("3", "3 보통"),
    ("4", "4"),
    ("5", "5 능숙"),
]

CONCERN_CHOICES = [
    ("what", "무엇을 물어야 할지 모름"),
    ("trust", "답을 믿어도 되는지"),
    ("privacy", "개인정보"),
    ("payment", "가입·결제"),
    ("english", "영어"),
    ("nothing", "특별히 없음"),
]

LEVEL_NAMES = ["입문", "초급", "중급"]

MAX_RAW_SCORE = 23


def compute_score(ai_tools, frequency, terms, ox, self_level):
    """써 본 AI(최대 3) + 빈도(0~4) + 용어(0~10) + OX(0~2) + 자기평가-1(0~4) = 23점 → 100점."""
    tools = len([t for t in (ai_tools or []) if t != "none"])
    raw = min(tools, 3)
    raw += int(frequency or 0)
    raw += sum(int(v) for v in (terms or {}).values())
    raw += sum(1 for key, _, answer in OX_QUESTIONS if (ox or {}).get(key) == answer)
    raw += max(int(self_level or 1) - 1, 0)
    return round(raw * 100 / MAX_RAW_SCORE)


def level_for(score):
    if score < 30:
        return "입문"
    if score < 60:
        return "초급"
    return "중급"


class PollResponse(models.Model):
    name = models.CharField("이름", max_length=50, unique=True)
    age = models.PositiveSmallIntegerField("나이")
    skill = models.CharField("컴퓨터·스마트폰 활용", max_length=20, choices=SKILL_CHOICES)
    ai_tools = models.JSONField("써 본 AI", default=list)
    frequency = models.CharField("사용 빈도", max_length=2, choices=FREQUENCY_CHOICES)
    uses = models.JSONField("주로 하는 일", default=list, blank=True)
    subscription = models.CharField("유료 구독", max_length=20, choices=SUBSCRIPTION_CHOICES)
    terms = models.JSONField("용어 이해도", default=dict)
    ox = models.JSONField("OX", default=dict)
    self_level = models.PositiveSmallIntegerField("자기 평가")
    concerns = models.JSONField("걱정되는 점", default=list, blank=True)
    wish = models.TextField("배우고 싶은 것", blank=True)
    score = models.PositiveSmallIntegerField("점수", default=0)
    level = models.CharField("수준", max_length=10, blank=True)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    submitted_at = models.DateTimeField("제출 시각", auto_now=True)

    class Meta:
        ordering = ["-submitted_at"]
        verbose_name = "AI 기초 설문 응답"
        verbose_name_plural = "AI 기초 설문 응답"

    def __str__(self):
        return f"{self.name} ({self.score}점)"

    def save(self, *args, **kwargs):
        self.score = compute_score(self.ai_tools, self.frequency, self.terms, self.ox, self.self_level)
        self.level = level_for(self.score)
        super().save(*args, **kwargs)
