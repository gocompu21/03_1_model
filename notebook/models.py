from django.db import models
from django.contrib.auth.models import User


class NotebookHistory(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notebook_histories"
    )
    user_input = models.TextField(verbose_name="질문")
    ai_response = models.TextField(verbose_name="답변")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="작성일시")
    response_time = models.FloatField(
        verbose_name="응답시간(초)", null=True, blank=True
    )
    is_success = models.BooleanField(default=True, verbose_name="성공여부")
    subject = models.CharField(max_length=50, verbose_name="과목", default="기본")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "지식저장소 기록"
        verbose_name_plural = "지식저장소 기록 목록"

    def __str__(self):
        return f"{self.user.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
