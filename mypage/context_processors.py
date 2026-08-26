"""마이페이지 사이드바에서 쓰는 값들.

메뉴 배지는 어느 화면에 있든 보여야 하므로 뷰마다 넘기지 않고
여기서 한 번에 채운다.
"""

from django.utils import timezone


def sidebar_counts(request):
    """오늘 복습할 문제 수와 오답 수."""
    if not request.user.is_authenticated:
        return {}

    # 마이페이지 밖에서는 쓰지 않으므로 굳이 세지 않는다
    if not request.path.startswith("/mypage/"):
        return {}

    from exam.models import UserQuestionResult

    from .models import ReviewSchedule, WrongAnswerExclusion

    review_count = ReviewSchedule.objects.filter(
        user=request.user,
        next_review_date__lte=timezone.localdate(),
        is_mastered=False,
    ).count()

    # 노트에서 빼 둔 문제는 세지 않는다 (목록과 숫자가 어긋나면 안 된다)
    excluded = WrongAnswerExclusion.objects.filter(
        user=request.user
    ).values_list("question_id", flat=True)

    wrong_count = (
        UserQuestionResult.objects.filter(
            attempt__user=request.user, is_correct=False
        )
        .exclude(question_id__in=excluded)
        .values("question_id")
        .distinct()
        .count()
    )

    return {
        "sidebar_review_count": review_count,
        "sidebar_wrong_count": wrong_count,
    }
