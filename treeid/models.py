from django.contrib.auth.models import User
from django.db import models


class TreeCourse(models.Model):
    """수목 식별 코스."""

    name = models.CharField(max_length=100, unique=True, verbose_name="코스명")
    description = models.CharField(max_length=200, blank=True, default="", verbose_name="설명")
    order = models.IntegerField(default=0, verbose_name="정렬 순서")
    is_active = models.BooleanField(default=True, verbose_name="활성")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "수목 식별 코스"
        verbose_name_plural = "수목 식별 코스"
        ordering = ["order", "id"]

    def __str__(self):
        return self.name

    @property
    def question_count(self):
        return self.questions.count()


class TreeQuestion(models.Model):
    """수목 사진 1장과 그에 대한 정보.

    해충·병해와 달리 수목은 정해진 정답 항목이 없고 특징 설명문이므로
    수목명과 설명을 그대로 담는다.
    """

    course = models.ForeignKey(
        TreeCourse, on_delete=models.CASCADE, related_name="questions", verbose_name="코스"
    )
    image = models.ImageField(upload_to="treeid/", verbose_name="수목 사진")
    order = models.IntegerField(default=0, verbose_name="순번")

    name = models.CharField(max_length=200, blank=True, default="", verbose_name="수목명")
    description = models.TextField(blank=True, default="", verbose_name="특징 설명")

    source_key = models.CharField(
        max_length=200, blank=True, default="", db_index=True, verbose_name="원본 식별자"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "수목 식별 문제"
        verbose_name_plural = "수목 식별 문제"
        ordering = ["course", "order", "id"]

    def __str__(self):
        return f"{self.course.name} #{self.order} - {self.name or '(이름없음)'}"

    def description_lines(self):
        """설명을 줄 단위로 나눠 반환 (화면에서 항목처럼 보여준다)."""
        return [ln.strip() for ln in self.description.split("\n") if ln.strip()]


class TreeBookmark(models.Model):
    """사용자가 관심 수목으로 등록한 문제."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="tree_bookmarks", verbose_name="사용자"
    )
    question = models.ForeignKey(
        TreeQuestion, on_delete=models.CASCADE, related_name="bookmarks", verbose_name="문제"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="등록 시각")

    class Meta:
        verbose_name = "관심 수목"
        verbose_name_plural = "관심 수목"
        unique_together = ("user", "question")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.question.name}"
