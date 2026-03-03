from django.db import models
from django.contrib.auth.models import User
from notebook.models import NotebookHistory
from chat.models import ChatHistory
from exam.models import Exam, Question


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


class StudyViewLog(models.Model):
    """Track when users view study pages"""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="study_view_logs", verbose_name="사용자"
    )
    exam_round = models.IntegerField(verbose_name="회차")
    viewed_at = models.DateTimeField(auto_now_add=True, verbose_name="열람 시간")

    class Meta:
        ordering = ["-viewed_at"]
        verbose_name = "학습 열람 기록"
        verbose_name_plural = "학습 열람 기록"

    def __str__(self):
        return f"{self.user.username} - {self.exam_round}회 학습 ({self.viewed_at})"


class RoundAnalysis(models.Model):
    """회차별 출제 동향 분석"""
    exam = models.OneToOneField(
        Exam, on_delete=models.CASCADE, related_name="analysis", verbose_name="회차"
    )
    # 기출 학습 분석 (과목별 집계)
    # {"수목병리학": {"similar": 12, "related": 8, "new": 5, "score": 66}, ...}
    past_exam_data = models.JSONField(default=dict, verbose_name="기출 학습 분석 데이터")
    past_exam_avg_score = models.IntegerField(verbose_name="기출 학습 평균 예상 점수")
    textbook_avg_score = models.FloatField(verbose_name="교과서 평균 예상 점수")
    summary = models.TextField(blank=True, verbose_name="분석 요약")
    # 상세 콘텐츠: 출제 영역, 경향 변화, 학습 전략 등
    detail_content = models.JSONField(default=dict, blank=True, verbose_name="상세 분석 콘텐츠")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")

    class Meta:
        verbose_name = "회차별 분석"
        verbose_name_plural = "회차별 분석"

    def __str__(self):
        return f"{self.exam.round_number}회 분석"


class QuestionAnalysis(models.Model):
    """문항별 교과서 커버리지 분석"""
    question = models.OneToOneField(
        Question, on_delete=models.CASCADE, related_name="analysis", verbose_name="문항"
    )
    textbook_possible = models.BooleanField(default=True, verbose_name="교과서 풀이 가능")
    textbook_reason = models.TextField(blank=True, default="", verbose_name="근거")

    class Meta:
        verbose_name = "문항 분석"
        verbose_name_plural = "문항 분석"

    def __str__(self):
        return f"Q{self.question.number} {'O' if self.textbook_possible else 'X'}"
