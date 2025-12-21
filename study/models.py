from django.db import models
from django.contrib.auth.models import User
from notebook.models import NotebookHistory
from chat.models import ChatHistory


class StudyQnA(models.Model):
    TYPE_CHOICES = [
        ("notebook", "Notebook"),
        ("chat", "Chat"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="study_qnas", verbose_name="사용자"
    )
    q_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, verbose_name="질문 유형"
    )

    # Optional links to original source
    related_notebook = models.ForeignKey(
        NotebookHistory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="study_qna_entries",
    )
    related_chat = models.ForeignKey(
        ChatHistory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="study_qna_entries",
    )

    question = models.TextField(verbose_name="질문 내용")
    answer = models.TextField(verbose_name="답변 내용")

    is_public = models.BooleanField(default=False, verbose_name="공개 여부")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="작성일시")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "학습 질의응답"
        verbose_name_plural = "학습 질의응답 목록"

    def __str__(self):
        return f"[{self.get_q_type_display()}] {self.question[:30]}..."
