from django.contrib.auth.models import User
from django.db import models


class DiseaseCourse(models.Model):
    """병해 식별 코스 (분류군 단위)."""

    name = models.CharField(max_length=100, unique=True, verbose_name="코스명")
    description = models.CharField(max_length=200, blank=True, default="", verbose_name="설명")
    order = models.IntegerField(default=0, verbose_name="정렬 순서")
    is_active = models.BooleanField(default=True, verbose_name="활성")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "병해 식별 코스"
        verbose_name_plural = "병해 식별 코스"
        ordering = ["order", "id"]

    def __str__(self):
        return self.name

    @property
    def question_count(self):
        return self.questions.count()


class DiseaseQuestion(models.Model):
    """병해 사진 1장과 그에 대한 정보.

    해충(pestid)과 달리 병해는 병명/기주/병원균/추가사항 체계라
    별도 모델로 둔다.
    """

    course = models.ForeignKey(
        DiseaseCourse, on_delete=models.CASCADE, related_name="questions", verbose_name="코스"
    )
    image = models.ImageField(upload_to="diseaseid/", verbose_name="병해 사진")
    order = models.IntegerField(default=0, verbose_name="순번")

    name = models.CharField(max_length=200, blank=True, default="", verbose_name="병명")
    host = models.CharField(max_length=200, blank=True, default="", verbose_name="기주")
    pathogen = models.CharField(max_length=300, blank=True, default="", verbose_name="병원균")
    note = models.CharField(max_length=300, blank=True, default="", verbose_name="추가사항")

    # 참고 정보
    taxonomy = models.CharField(max_length=200, blank=True, default="", verbose_name="분류")
    alt_host = models.CharField(max_length=200, blank=True, default="", verbose_name="중간기주")

    # 기출 이력
    exam_stars = models.IntegerField(default=0, db_index=True, verbose_name="기출 중요도")
    exam_note = models.CharField(max_length=200, blank=True, default="", verbose_name="기출 회차")

    source_key = models.CharField(
        max_length=200, blank=True, default="", db_index=True, verbose_name="원본 식별자"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # 화면에 정답으로 보여줄 항목
    FIELD_LABELS = {
        "name": "병명",
        "host": "기주",
        "pathogen": "병원균",
        "note": "추가사항",
    }

    class Meta:
        verbose_name = "병해 식별 문제"
        verbose_name_plural = "병해 식별 문제"
        ordering = ["course", "order", "id"]

    def __str__(self):
        return f"{self.course.name} #{self.order} - {self.name or '(이름없음)'}"

    @property
    def is_past(self):
        return self.exam_stars > 0

    def answer_fields(self):
        """값이 채워진 항목만 [(키, 라벨, 값)] 로 반환."""
        result = []
        for key, label in self.FIELD_LABELS.items():
            value = getattr(self, key, "")
            if value:
                result.append((key, label, value))
        return result


class DiseaseBookmark(models.Model):
    """사용자가 관심 병해로 등록한 문제."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="disease_bookmarks", verbose_name="사용자"
    )
    question = models.ForeignKey(
        DiseaseQuestion, on_delete=models.CASCADE, related_name="bookmarks", verbose_name="문제"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="등록 시각")

    class Meta:
        verbose_name = "관심 병해"
        verbose_name_plural = "관심 병해"
        unique_together = ("user", "question")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.question.name}"
