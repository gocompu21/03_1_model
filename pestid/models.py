from django.contrib.auth.models import User
from django.db import models


class PestCourse(models.Model):
    """해충 식별 코스 (원본 마라톤의 폴더 하나에 대응)."""

    name = models.CharField(max_length=100, unique=True, verbose_name="코스명")
    description = models.CharField(max_length=200, blank=True, default="", verbose_name="설명")
    order = models.IntegerField(default=0, verbose_name="정렬 순서")
    is_active = models.BooleanField(default=True, verbose_name="활성")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "해충 식별 코스"
        verbose_name_plural = "해충 식별 코스"
        ordering = ["order", "id"]

    def __str__(self):
        return self.name

    @property
    def question_count(self):
        return self.questions.count()


class PestQuestion(models.Model):
    """해충 사진 1장과 그에 대한 정답 항목들.

    정답 필드는 원본 마라톤의 answers 구조를 그대로 따른다.
    쉼표로 구분된 복수 정답을 허용하며, 채점 시 공백을 제거하고 비교한다.
    비어 있는 항목은 출제하지 않는다.
    """

    course = models.ForeignKey(
        PestCourse, on_delete=models.CASCADE, related_name="questions", verbose_name="코스"
    )
    image = models.ImageField(upload_to="pestid/", verbose_name="해충 사진")
    order = models.IntegerField(default=0, verbose_name="순번")

    name = models.CharField(max_length=200, blank=True, default="", verbose_name="해충명")
    occurrence = models.CharField(max_length=200, blank=True, default="", verbose_name="연발생횟수")
    overwinter = models.CharField(max_length=200, blank=True, default="", verbose_name="월동태")
    host = models.CharField(max_length=200, blank=True, default="", verbose_name="여름기주")

    source_key = models.CharField(
        max_length=200, blank=True, default="", db_index=True,
        verbose_name="원본 식별자", help_text="임포트 시 중복 방지용 (원본 파일명 등)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # 필드명 -> 화면 표시 라벨 (원본 FIELD_MAP과 동일)
    FIELD_LABELS = {
        "name": "해충명",
        "occurrence": "연발생횟수",
        "overwinter": "월동태",
        "host": "여름기주",
    }

    class Meta:
        verbose_name = "해충 식별 문제"
        verbose_name_plural = "해충 식별 문제"
        ordering = ["course", "order", "id"]

    def __str__(self):
        return f"{self.course.name} #{self.order} - {self.name or '(이름없음)'}"

    def answer_fields(self):
        """값이 채워진 정답 항목만 [(키, 라벨, 정답문자열)] 로 반환."""
        result = []
        for key, label in self.FIELD_LABELS.items():
            value = getattr(self, key, "")
            if value:
                result.append((key, label, value))
        return result

    def accepted_answers(self, key):
        """해당 항목의 허용 정답 목록 (공백 제거)."""
        raw = getattr(self, key, "") or ""
        return [a.replace(" ", "") for a in raw.split(",") if a.strip()]

    def is_correct(self, key, user_input):
        """사용자 입력이 정답인지 판정. 공백을 무시하고 비교한다."""
        cleaned = (user_input or "").replace(" ", "")
        if not cleaned:
            return False
        return cleaned in self.accepted_answers(key)


class PestAttempt(models.Model):
    """사용자의 코스 1회 도전 기록."""

    MODE_CHOICES = [
        ("choice", "객관식"),
        ("typing", "주관식"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="pest_attempts", verbose_name="사용자"
    )
    course = models.ForeignKey(
        PestCourse, on_delete=models.CASCADE, related_name="attempts", verbose_name="코스"
    )
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default="choice", verbose_name="모드")
    total_count = models.IntegerField(default=0, verbose_name="문제 수")
    correct_count = models.IntegerField(default=0, verbose_name="정답 수")
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="시작 시각")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="완료 시각")

    class Meta:
        verbose_name = "해충 식별 도전"
        verbose_name_plural = "해충 식별 도전"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.user.username} - {self.course.name} ({self.correct_count}/{self.total_count})"

    @property
    def score_percent(self):
        if not self.total_count:
            return 0
        return round(self.correct_count * 100 / self.total_count)
