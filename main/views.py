from django.db.models import Count
from django.shortcuts import render

from diseaseid.models import DiseaseQuestion
from dvdexam.models import Exam
from pestid.models import PestCourse, PestQuestion
from treeid.models import TreeQuestion


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
    disease_question_count = DiseaseQuestion.objects.filter(course__is_active=True).count()
    tree_question_count = TreeQuestion.objects.filter(course__is_active=True).count()
    exam_count = (
        Exam.objects.filter(is_active=True)
        .annotate(q_count=Count("questions"))
        .filter(q_count__gt=0)
        .count()
    )

    return render(request, "main/dvd.html", {
        "pest_course_count": pest_course_count,
        "pest_question_count": pest_question_count,
        "disease_question_count": disease_question_count,
        "tree_question_count": tree_question_count,
        "exam_count": exam_count,
    })
