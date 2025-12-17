from django.db import models
from django.contrib.auth.models import User


class Exam(models.Model):
    round_number = models.IntegerField(unique=True, verbose_name="회차")

    def __str__(self):
        return f"{self.round_number}회"


class Subject(models.Model):
    name = models.CharField(max_length=50, verbose_name="과목명")
    code = models.IntegerField(unique=True, verbose_name="과목 코드")

    def __str__(self):
        return self.name


class Question(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="questions")
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="questions"
    )
    number = models.IntegerField(verbose_name="문제 번호")
    content = models.TextField(verbose_name="문제 지문")
    image = models.ImageField(
        upload_to="questions/images/", blank=True, null=True, verbose_name="문제 이미지"
    )

    choice1 = models.CharField(max_length=200, verbose_name="보기 1")
    choice2 = models.CharField(max_length=200, verbose_name="보기 2")
    choice3 = models.CharField(max_length=200, verbose_name="보기 3")
    choice4 = models.CharField(max_length=200, verbose_name="보기 4")
    choice5 = models.CharField(max_length=200, verbose_name="보기 5")

    answer = models.IntegerField(verbose_name="정답 (1-5)")
    general_chat = models.TextField(verbose_name="해설")
    textbook_chat = models.TextField(verbose_name="기본서 해설", blank=True, null=True)
    infographic_image = models.ImageField(
        upload_to="questions/explanations/",
        blank=True,
        null=True,
        verbose_name="인포그래픽 이미지",
    )

    class Meta:
        ordering = ["exam", "number"]
        unique_together = ("exam", "number")

    def __str__(self):
        return f"{self.exam.round_number}회 - {self.number}번"


class UserExamAttempt(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="exam_attempts"
    )
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    subjects = models.ManyToManyField(Subject, verbose_name="응시 과목")
    start_time = models.DateTimeField(auto_now_add=True, verbose_name="시작 시간")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="종료 시간")
    total_score = models.IntegerField(null=True, blank=True, verbose_name="총점")

    def __str__(self):
        return f"{self.user.username} - {self.exam.round_number}회 응시 ({self.start_time})"


class UserQuestionResult(models.Model):
    attempt = models.ForeignKey(
        UserExamAttempt, on_delete=models.CASCADE, related_name="results"
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.IntegerField(verbose_name="선택 답안")
    is_correct = models.BooleanField(verbose_name="정답 여부")

    def __str__(self):
        return f"{self.attempt} - {self.question.number}번 결과"
