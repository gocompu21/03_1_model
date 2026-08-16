from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models import Count, Max, Q
from django.shortcuts import render
from django.utils import timezone

from diseaseid.models import DiseaseQuestion
from dvdexam.models import Exam
from pestid.models import PestCourse, PestQuestion
from treeid.models import TreeQuestion


def index(request):
    """첫 화면. 사이트가 돌아가는 모습을 먼저 보여준다.

    최근 글·자료 현황·학습 현황을 위에 두고 메뉴는 아래로 내린다.
    로그인하지 않았으면 소개만 보여준다(학습 현황은 개인 정보다).
    """
    return render(request, "main/index.html", {
        "recent_posts": _recent_posts(),
        "content_stats": _content_stats(),
        "activity": _activity(request.user),
    })


def _recent_posts(limit=6):
    """질문 공유방 최근 글."""
    from bbs.models import Post

    return (
        Post.objects.select_related("author", "type")
        .annotate(comment_count=Count("comments"))
        .order_by("-created_at")[:limit]
    )


def _content_stats():
    """자료 등록 현황. 화면에 그대로 뿌릴 수 있는 형태로 만든다."""
    from exam.models import Question, StudyNote
    from glossary.models import Term
    from lecture.models import Lecture
    from practice.models import ChapterContent

    dvd_total = (
        TreeQuestion.objects.filter(course__is_active=True).count()
        + DiseaseQuestion.objects.filter(course__is_active=True).count()
        + PestQuestion.objects.filter(course__is_active=True).count()
    )
    exam_count = (
        Exam.objects.filter(is_active=True)
        .annotate(q_count=Count("questions"))
        .filter(q_count__gt=0)
        .count()
    )

    return [
        {"key": "practice", "icon": "📗", "name": "기본서 학습",
         "n": ChapterContent.objects.count(), "unit": "단원",
         "url": "practice:book_list"},
        {"key": "lecture", "icon": "🎬", "name": "녹화강의",
         "n": Lecture.objects.filter(is_active=True).count(), "unit": "편",
         "url": "lecture:index"},
        {"key": "note", "icon": "📝", "name": "쪽집게 노트",
         "n": StudyNote.objects.count(), "unit": "장",
         "url": "study:index"},
        {"key": "question", "icon": "📖", "name": "기출문제",
         "n": Question.objects.count(), "unit": "문항",
         "url": "study:index"},
        {"key": "term", "icon": "🔎", "name": "기출용어",
         "n": Term.objects.count(), "unit": "개",
         "url": "glossary:term_list"},
        {"key": "dvd", "icon": "📀", "name": "DVD 암기",
         "n": dvd_total, "unit": "종",
         "url": "main:dvd"},
        {"key": "dvdexam", "icon": "🎯", "name": "DVD 시험",
         "n": exam_count, "unit": "개",
         "url": "dvdexam:index"},
    ]


def _activity(user):
    """학습 현황.

    로그인했으면 '내 현황'과 함께 최근 활동한 사람들을 보여주고,
    로그인 전이면 사람 수만 보여준다(개인 정보를 드러내지 않는다).
    """
    week_ago = timezone.now() - timedelta(days=7)
    real = User.objects.filter(is_active=True).exclude(username__startswith="_")
    data = {
        "week_users": real.filter(last_login__gte=week_ago).count(),
        "total_users": real.count(),
        "recent": [],
        "me": None,
    }

    if not user.is_authenticated:
        return data

    # 최근 다녀간 사람 (이름만. 무엇을 했는지는 드러내지 않는다)
    # 검증용 임시 계정(_로 시작)은 빼되, 보고 있는 본인은 언제나 넣는다
    data["recent"] = [
        {
            "name": u.first_name or u.username,
            "last_login": u.last_login,
            "is_me": u.id == user.id,
        }
        for u in User.objects.filter(is_active=True, last_login__isnull=False)
        .exclude(Q(username__startswith="_") & ~Q(id=user.id))
        .order_by("-last_login")[:8]
    ]

    data["me"] = _my_progress(user)
    return data


def _my_progress(user):
    """내가 얼마나 했는지."""
    from dvdexam.models import ExamAttempt
    from lecture.models import LectureView
    from study.models import StudyViewLog

    return {
        "studied": StudyViewLog.objects.filter(user=user).count(),
        "lectures": LectureView.objects.filter(user=user).count(),
        "exams": ExamAttempt.objects.filter(
            user=user, submitted_at__isnull=False
        ).count(),
    }


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
