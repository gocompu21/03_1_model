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
        If correct: advance to next interval (from TODAY)
        If wrong: reset to first interval
        """
        from django.utils import timezone

        today = timezone.localdate()

        if is_correct:
            self.review_count += 1
            if self.review_count >= len(self.REVIEW_INTERVALS):
                self.is_mastered = True
                self.next_review_date = today  # Keep current date
            else:
                # Calculate next review from TODAY (Anki/SuperMemo style)
                interval = self.REVIEW_INTERVALS[self.review_count]
                self.next_review_date = today + timedelta(days=interval)
        else:
            # Reset if answered wrong again
            self.review_count = 0
            self.last_wrong_date = timezone.now()
            self.is_mastered = False
            # Next review tomorrow
            self.next_review_date = today + timedelta(days=self.REVIEW_INTERVALS[0])

        self.save()


class WrongAnswerExclusion(models.Model):
    """오답노트에서 빼 둔 문제.

    이미 익힌 문제가 목록에 계속 남아 방해되므로 사용자가 직접 뺀다.
    기록을 지우지 않고 표시만 남기므로 언제든 되돌릴 수 있다.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="wrong_exclusions",
        verbose_name="사용자",
    )
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="wrong_exclusions",
        verbose_name="문제",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="제외한 날")

    class Meta:
        verbose_name = "오답노트 제외"
        verbose_name_plural = "오답노트 제외"
        # 같은 문제를 두 번 뺄 일은 없다
        unique_together = ("user", "question")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.question} 제외"
