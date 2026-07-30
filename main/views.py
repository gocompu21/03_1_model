from django.db.models import Count
from django.shortcuts import render

from pestid.models import PestCourse, PestQuestion


def index(request):
    return render(request, "main/index.html")


def dvd(request):
    """사진·영상으로 익히는 학습 콘텐츠 모음."""
    pest_course_count = (
        PestCourse.objects.filter(is_active=True)
        .annotate(q_count=Count("questions"))
        .filter(q_count__gt=0)
        .count()
    )

    pest_question_count = PestQuestion.objects.filter(course__is_active=True).count()

    return render(request, "main/dvd.html", {
        "pest_course_count": pest_course_count,
        "pest_question_count": pest_question_count,
    })
