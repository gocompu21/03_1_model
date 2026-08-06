import json

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Exam, ExamAnswer, ExamAttempt, ExamQuestion, build_questions, source_pool


def _is_admin(user):
    return user.is_authenticated and user.is_staff


# ---------------------------------------------------------------- 응시자

@login_required
def index(request):
    """응시할 수 있는 시험 목록."""
    exams = (
        Exam.objects.filter(is_active=True)
        .annotate(q_count=Count("questions"))
        .filter(q_count__gt=0)
        .order_by("kind", "-created_at")
    )

    mine = {
        a.exam_id: a
        for a in ExamAttempt.objects.filter(user=request.user, exam__in=exams)
    }
    for exam in exams:
        exam.my_attempt = mine.get(exam.id)

    return render(request, "dvdexam/index.html", {
        "always": [e for e in exams if e.kind == "always"],
        "live": [e for e in exams if e.kind == "live"],
        "now": timezone.now(),
    })


@login_required
def take(request, exam_id):
    """응시 화면. 이미 제출했으면 결과로 보낸다."""
    exam = get_object_or_404(Exam, id=exam_id, is_active=True)

    attempt = ExamAttempt.objects.filter(exam=exam, user=request.user).first()
    if attempt and attempt.is_submitted:
        return redirect("dvdexam:result", exam_id=exam.id)

    state = exam.live_state
    if state != "open":
        return render(request, "dvdexam/closed.html", {"exam": exam, "state": state})

    if not attempt:
        attempt = ExamAttempt.objects.create(
            exam=exam, user=request.user, total=exam.questions.count()
        )

    deadline = exam.deadline_for(attempt)
    if deadline and timezone.now() >= deadline:
        _grade(attempt, {}, auto=True)
        return redirect("dvdexam:result", exam_id=exam.id)

    payload = [
        {
            "id": q.id,
            "no": q.order,
            "image": q.image_url,
            "choices": q.choices,
        }
        for q in exam.questions.all()
    ]

    return render(request, "dvdexam/take.html", {
        "exam": exam,
        "attempt": attempt,
        "questions_json": json.dumps(payload, ensure_ascii=False),
        "total": len(payload),
        "deadline_ms": int(deadline.timestamp() * 1000) if deadline else 0,
    })


@login_required
def submit(request, exam_id):
    """제출. 채점은 서버에서만 한다."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    exam = get_object_or_404(Exam, id=exam_id, is_active=True)
    attempt = ExamAttempt.objects.filter(exam=exam, user=request.user).first()
    if not attempt:
        return JsonResponse({"error": "no attempt"}, status=404)
    if attempt.is_submitted:
        return JsonResponse({"ok": True, "already": True, "url": f"/dvdexam/{exam.id}/result/"})

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid json"}, status=400)

    given = {int(k): (v or "") for k, v in (body.get("answers") or {}).items()}
    _grade(attempt, given, auto=bool(body.get("auto")))

    return JsonResponse({
        "ok": True,
        "score": attempt.score,
        "total": attempt.total,
        "url": f"/dvdexam/{exam.id}/result/",
    })


def _grade(attempt, given, auto=False):
    """응답을 저장하고 점수를 매긴다."""
    questions = list(attempt.exam.questions.all())
    score = 0

    for q in questions:
        value = (given.get(q.id) or "").strip()
        correct = q.is_correct(value) if value else False
        if correct:
            score += 1
        ExamAnswer.objects.update_or_create(
            attempt=attempt, question=q,
            defaults={"given": value[:200], "is_correct": correct},
        )

    attempt.score = score
    attempt.total = len(questions)
    attempt.submitted_at = timezone.now()
    attempt.auto_submitted = auto
    attempt.save(update_fields=["score", "total", "submitted_at", "auto_submitted"])


@login_required
def result(request, exam_id):
    """내 채점 결과."""
    exam = get_object_or_404(Exam, id=exam_id)
    attempt = get_object_or_404(ExamAttempt, exam=exam, user=request.user)
    answers = attempt.answers.select_related("question").order_by("question__order")

    return render(request, "dvdexam/result.html", {
        "exam": exam,
        "attempt": attempt,
        "answers": answers,
    })


# ---------------------------------------------------------------- 관리자

@user_passes_test(_is_admin)
def manage(request):
    """시험 관리: 등록 + 목록."""
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "delete":
            Exam.objects.filter(id=request.POST.get("exam_id")).delete()
            return redirect("dvdexam:manage")

        if action == "toggle":
            exam = Exam.objects.filter(id=request.POST.get("exam_id")).first()
            if exam:
                exam.is_active = not exam.is_active
                exam.save(update_fields=["is_active"])
            return redirect("dvdexam:manage")

        exam = Exam(
            title=(request.POST.get("title") or "").strip()[:120],
            subject=request.POST.get("subject", "tree"),
            kind=request.POST.get("kind", "always"),
            answer_format=request.POST.get("answer_format", "choice"),
            created_by=request.user,
        )
        try:
            exam.question_count = max(1, min(100, int(request.POST.get("question_count", 20))))
        except (TypeError, ValueError):
            exam.question_count = 20
        try:
            exam.time_limit_min = max(0, int(request.POST.get("time_limit_min", 0)))
        except (TypeError, ValueError):
            exam.time_limit_min = 0

        if exam.kind == "live":
            exam.start_at = _parse_dt(request.POST.get("start_at"))
            exam.end_at = _parse_dt(request.POST.get("end_at"))

        if not exam.title:
            exam.title = f"{exam.get_subject_display()} {exam.get_answer_format_display()}"

        exam.save()
        made = build_questions(exam)
        if not made:
            exam.delete()

        return redirect("dvdexam:manage")

    exams = Exam.objects.annotate(
        q_count=Count("questions", distinct=True),
        attempt_count=Count("attempts", distinct=True),
    ).order_by("-created_at")

    subjects = [
        {"key": key, "label": label, "count": len(source_pool(key))}
        for key, label in Exam.SUBJECT_CHOICES
    ]

    return render(request, "dvdexam/manage.html", {
        "exams": exams,
        "subjects": subjects,
        "kind_choices": Exam.KIND_CHOICES,
        "format_choices": Exam.FORMAT_CHOICES,
        "now": timezone.now(),
    })


def _parse_dt(value):
    """<input type="datetime-local"> 값을 파싱한다."""
    if not value:
        return None
    parsed = timezone.datetime.fromisoformat(value)
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    return parsed


@user_passes_test(_is_admin)
def scores(request, exam_id):
    """응시 결과 모아 보기."""
    exam = get_object_or_404(Exam, id=exam_id)
    attempts = (
        exam.attempts.select_related("user")
        .order_by("-score", "submitted_at")
    )
    submitted = [a for a in attempts if a.is_submitted]
    average = round(sum(a.score_percent for a in submitted) / len(submitted)) if submitted else 0

    return render(request, "dvdexam/scores.html", {
        "exam": exam,
        "attempts": attempts,
        "submitted_count": len(submitted),
        "average": average,
    })
