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

    answer = models.JSONField(default=list, verbose_name="정답 (1-5, 복수 가능)")
    general_chat = models.TextField(verbose_name="해설")
    textbook_chat = models.TextField(verbose_name="기본서 해설", blank=True, null=True)
    infographic_image = models.ImageField(
        upload_to="questions/explanations/",
        blank=True,
        null=True,
        verbose_name="인포그래픽 이미지",
    )
    narration = models.TextField(verbose_name="나레이션", blank=True, null=True)
    summary = models.CharField(max_length=50, verbose_name="문제 요약", blank=True, null=True)

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
    ai_analysis = models.TextField(null=True, blank=True, verbose_name="AI 분석 리포트")

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


class TopicQuestionSet(models.Model):
    """주제별 문제집"""
    title = models.CharField(max_length=200, verbose_name="문제집 제목")
    description = models.TextField(blank=True, verbose_name="설명")
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True, related_name='topic_sets', verbose_name="과목")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='topic_sets')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    is_public = models.BooleanField(default=True, verbose_name="공개 여부")
    order = models.IntegerField(default=0, verbose_name="정렬 순서")
    
    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = "주제별 문제집"
        verbose_name_plural = "주제별 문제집"
    
    def __str__(self):
        return self.title
    
    def question_count(self):
        return self.items.count()


class TopicQuestionSetItem(models.Model):
    """문제집-문제 연결 (순서 유지용)"""
    question_set = models.ForeignKey(TopicQuestionSet, on_delete=models.CASCADE, related_name='items')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.IntegerField(verbose_name="순서")
    
    class Meta:
        ordering = ['order']
        unique_together = ['question_set', 'order']
        verbose_name = "문제집 항목"
        verbose_name_plural = "문제집 항목"
    
    def __str__(self):
        return f"{self.question_set.title} - {self.order}번"


class UserTopicSetAttempt(models.Model):
    """주제별 문제집 응시 기록"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='topic_attempts')
    question_set = models.ForeignKey(TopicQuestionSet, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True, verbose_name="시작 시간")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="종료 시간")
    total_score = models.IntegerField(null=True, blank=True, verbose_name="총점")
    
    class Meta:
        ordering = ['-start_time']
        verbose_name = "주제별 문제집 응시"
        verbose_name_plural = "주제별 문제집 응시"
    
    def __str__(self):
        return f"{self.user.username} - {self.question_set.title} ({self.start_time})"


class UserTopicQuestionResult(models.Model):
    """주제별 문제집 문제 결과"""
    attempt = models.ForeignKey(UserTopicSetAttempt, on_delete=models.CASCADE, related_name='results')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.IntegerField(verbose_name="선택 답안")
    is_correct = models.BooleanField(verbose_name="정답 여부")
    
    class Meta:
        verbose_name = "주제별 문제 결과"
        verbose_name_plural = "주제별 문제 결과"
    
    def __str__(self):
        return f"{self.attempt} - {self.question} 결과"
