"""녹화강의 — 외부에 올린 영상 링크를 과목·교시별로 모아 둔다.

영상 파일은 직접 보관하지 않는다. 네이버 등에 올린 주소를 등록하면
사용자가 과목을 골라 그 링크로 찾아가는 구조다.
"""

from django.contrib.auth.models import User
from django.db import models

from exam.models import Subject


class Lecture(models.Model):
    """녹화강의 한 편."""

    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="lectures", verbose_name="과목"
    )
    lecture_date = models.DateField(verbose_name="일시")
    period = models.IntegerField(default=1, verbose_name="교시")
    title = models.CharField(max_length=200, verbose_name="내용")
    duration_min = models.IntegerField(
        default=0, verbose_name="시간(분)", help_text="0이면 표시하지 않는다"
    )
    video_url = models.URLField(
        max_length=500, verbose_name="영상 링크",
        help_text="네이버 등에 올린 주소 (예: https://naver.me/FvTbwUsX)",
    )
    note = models.TextField(blank=True, default="", verbose_name="비고")

    is_active = models.BooleanField(default=True, verbose_name="공개")
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_lectures", verbose_name="등록자",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "녹화강의"
        verbose_name_plural = "녹화강의"
        # 최근 강의가 위로. 같은 날이면 교시 순서대로 본다
        ordering = ["-lecture_date", "period", "id"]

    def __str__(self):
        return f"[{self.subject.name}] {self.lecture_date} {self.period}교시 {self.title}"

    @property
    def duration_display(self):
        """'1시간 30분' 형태로. 0이면 빈 문자열."""
        if not self.duration_min:
            return ""
        hours, minutes = divmod(self.duration_min, 60)
        if hours and minutes:
            return f"{hours}시간 {minutes}분"
        if hours:
            return f"{hours}시간"
        return f"{minutes}분"


class LectureView(models.Model):
    """누가 어떤 강의를 몇 번 열었는지.

    영상은 네이버 등 외부에서 재생되므로 **실제 시청 시간은 알 수 없다.**
    사이트가 확인할 수 있는 것은 '강의 보기를 눌러 영상으로 나갔다'는
    사실뿐이다. 그래서 시간이 아니라 횟수와 시각만 남긴다.
    """

    lecture = models.ForeignKey(
        Lecture, on_delete=models.CASCADE, related_name="views", verbose_name="강의"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="lecture_views", verbose_name="사용자"
    )
    count = models.IntegerField(default=0, verbose_name="시청 횟수")
    first_viewed_at = models.DateTimeField(auto_now_add=True, verbose_name="처음 시청")
    last_viewed_at = models.DateTimeField(auto_now=True, verbose_name="마지막 시청")

    class Meta:
        verbose_name = "녹화강의 시청"
        verbose_name_plural = "녹화강의 시청"
        # 사용자 한 명당 강의 하나에 한 행. 다시 보면 count만 올린다
        unique_together = ("lecture", "user")
        ordering = ["-last_viewed_at"]

    def __str__(self):
        return f"{self.user.username} - {self.lecture.title} ({self.count}회)"
