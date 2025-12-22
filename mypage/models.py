from django.db import models
from django.contrib.auth.models import User
from exam.models import Question
from datetime import timedelta


class ReviewSchedule(models.Model):
    """
    Tracks spaced repetition review schedule for each user's wrong answers.
    Based on Ebbinghaus forgetting curve: 1 -> 3 -> 7 -> 14 -> 30 days
    """

    REVIEW_INTERVALS = [1, 3, 7, 14, 30]  # Days until next review

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="review_schedules"
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    last_wrong_date = models.DateTimeField(verbose_name="마지막 오답 일시")
    review_count = models.IntegerField(default=0, verbose_name="복습 횟수")
    next_review_date = models.DateField(verbose_name="다음 복습 예정일")
    is_mastered = models.BooleanField(default=False, verbose_name="완전 학습 여부")

    class Meta:
        unique_together = ("user", "question")
        ordering = ["next_review_date"]

    def __str__(self):
        return f"{self.user.username} - Q{self.question.number} (복습 {self.review_count}회)"

    def calculate_next_review_date(self):
        """Calculate next review date based on review count."""
        if self.review_count >= len(self.REVIEW_INTERVALS):
            self.is_mastered = True
            return self.next_review_date

        interval = self.REVIEW_INTERVALS[self.review_count]
        return self.last_wrong_date.date() + timedelta(days=interval)

    def mark_reviewed(self, is_correct):
        """
        Update schedule after a review session.
        If correct: advance to next interval
        If wrong: reset to first interval
        """
        from django.utils import timezone

        if is_correct:
            self.review_count += 1
            if self.review_count >= len(self.REVIEW_INTERVALS):
                self.is_mastered = True
        else:
            # Reset if answered wrong again
            self.review_count = 0
            self.last_wrong_date = timezone.now()
            self.is_mastered = False

        self.next_review_date = self.calculate_next_review_date()
        self.save()
