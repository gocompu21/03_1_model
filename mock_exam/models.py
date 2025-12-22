from django.db import models
from django.contrib.auth.models import User
from exam.models import Question


class MockExam(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mock_exams")
    start_time = models.DateTimeField(auto_now_add=True, verbose_name="시작 시간")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="종료 시간")
    score = models.IntegerField(null=True, blank=True, verbose_name="총점")
    is_completed = models.BooleanField(default=False, verbose_name="완료 여부")

    def __str__(self):
        return f"{self.user.username} - Mock Exam ({self.start_time.strftime('%Y-%m-%d %H:%M')})"


class MockExamQuestion(models.Model):
    mock_exam = models.ForeignKey(
        MockExam, on_delete=models.CASCADE, related_name="questions"
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.IntegerField(
        null=True, blank=True, verbose_name="선택 답안"
    )
    is_correct = models.BooleanField(default=False, verbose_name="정답 여부")

    def __str__(self):
        return f"Mock {self.mock_exam.id} - Q{self.question.number}"
