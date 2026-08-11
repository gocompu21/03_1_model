import json

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q
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
    """응시 화면.

    이미 제출했으면 결과로 보낸다. ?retry=1 로 들어오면 다시 푼다
    (이전 기록을 지우고 새로 시작한다).
    """
    exam = get_object_or_404(Exam, id=exam_id, is_active=True)

    attempt = ExamAttempt.objects.filter(exam=exam, user=request.user).first()
    retry = request.GET.get("retry") == "1"

    if attempt and attempt.is_submitted and not retry:
        return redirect("dvdexam:result", exam_id=exam.id)

    state = exam.live_state
    if state != "open":
        return render(request, "dvdexam/closed.html", {"exam": exam, "state": state})

    if attempt and retry:
        # 같은 문제로 처음부터 다시 푼다. 이전 답과 점수는 지운다.
        attempt.answers.all().delete()
        attempt.score = 0
        attempt.submitted_at = None
        attempt.auto_submitted = False
        attempt.last_saved_at = None
        attempt.started_at = timezone.now()
        attempt.total = exam.questions.count()
        attempt.save(update_fields=[
            "score", "submitted_at", "auto_submitted",
            "last_saved_at", "started_at", "total",
        ])

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
def save(request, exam_id):
    """응시 중 답안을 중간 저장한다.

    채점은 하지 않고 응답만 남긴다. 브라우저가 닫히거나 시간이 끝나도
    여기까지 푼 내용은 살아 있다.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    exam = get_object_or_404(Exam, id=exam_id, is_active=True)
    attempt = ExamAttempt.objects.filter(exam=exam, user=request.user).first()
    if not attempt or attempt.is_submitted:
        return JsonResponse({"ok": False, "submitted": True})

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid json"}, status=400)

    given = {int(k): (v or "") for k, v in (body.get("answers") or {}).items()}
    questions = {q.id: q for q in exam.questions.all()}

    for qid, value in given.items():
        q = questions.get(qid)
        if not q:
            continue
        value = value.strip()
        # 저장 시점에 정답 여부까지 판정해 둔다. 관리자 화면에서 푼 문항
        # 기준 점수를 실시간으로 보여주기 위해서다 (응시자에게는 알리지 않는다)
        ExamAnswer.objects.update_or_create(
            attempt=attempt, question=q,
            defaults={"given": value[:200], "is_correct": q.is_correct(value) if value else False},
        )

    attempt.last_saved_at = timezone.now()
    attempt.save(update_fields=["last_saved_at"])

    return JsonResponse({"ok": True, "answered": attempt.answered_count})


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
    """응답을 저장하고 점수를 매긴다.

    given에 없는 문항은 중간 저장해 둔 답을 쓴다. 시간이 끝나 자동
    제출될 때 브라우저가 답을 못 보내도 저장분으로 채점하기 위해서다.
    """
    questions = list(attempt.exam.questions.all())
    saved = {a.question_id: a.given for a in attempt.answers.all()}
    score = 0

    for q in questions:
        value = (given.get(q.id) if q.id in given else saved.get(q.id)) or ""
        value = value.strip()
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


@login_required
def overview(request, exam_id):
    """전체 시험현황. 문항별 정답과 정답률을 보여준다.

    응시자도 볼 수 있다. 다만 아직 제출하지 않았다면 정답이 새므로 막는다.
    """
    exam = get_object_or_404(Exam, id=exam_id)

    if not _is_admin(request.user):
        mine = ExamAttempt.objects.filter(exam=exam, user=request.user).first()
        if not mine or not mine.is_submitted:
            return render(request, "dvdexam/locked.html", {"exam": exam})

    return render(request, "dvdexam/overview.html", _overview_data(exam, request.user))


def _overview_data(exam, user):
    """문항별 정답률과 전체 집계를 만든다."""
    questions = list(exam.questions.all())
    answers = list(
        ExamAnswer.objects.filter(attempt__exam=exam)
        .exclude(given="")
        .values("question_id", "is_correct")
    )

    solved, correct = {}, {}
    for a in answers:
        qid = a["question_id"]
        solved[qid] = solved.get(qid, 0) + 1
        if a["is_correct"]:
            correct[qid] = correct.get(qid, 0) + 1

    # 내가 어떻게 답했는지 (관리자는 응시 기록이 없을 수 있다)
    mine = {
        a.question_id: a
        for a in ExamAnswer.objects.filter(attempt__exam=exam, attempt__user=user)
    }

    rows = []
    for q in questions:
        n = solved.get(q.id, 0)
        hit = correct.get(q.id, 0)
        my = mine.get(q.id)
        rows.append({
            "id": q.id,
            "no": q.order,
            "image": q.image_url,
            "answer": q.answer,
            "solved": n,
            "correct": hit,
            "rate": round(hit * 100 / n) if n else None,   # 푼 사람 기준
            "my_given": my.given if my else "",
            "my_correct": my.is_correct if my else None,
        })

    graded = [r for r in rows if r["rate"] is not None]
    attempts = exam.attempts.all()
    submitted = [a for a in attempts if a.is_submitted]

    return {
        "exam": exam,
        "rows": rows,
        "hardest": sorted(graded, key=lambda r: r["rate"])[:5],
        "stats": {
            "total_q": len(questions),
            "taking": attempts.count(),
            "submitted": len(submitted),
            "average": round(sum(a.score_percent for a in submitted) / len(submitted))
                       if submitted else 0,
            "avg_rate": round(sum(r["rate"] for r in graded) / len(graded)) if graded else 0,
        },
        "is_admin": _is_admin(user),
    }


@login_required
def review(request, exam_id):
    """복습하기. 반 전체가 많이 틀린 순으로 사진을 넘겨본다."""
    exam = get_object_or_404(Exam, id=exam_id)

    if not _is_admin(request.user):
        mine = ExamAttempt.objects.filter(exam=exam, user=request.user).first()
        if not mine or not mine.is_submitted:
            return render(request, "dvdexam/locked.html", {"exam": exam})

    data = _overview_data(exam, request.user)

    # 아무도 풀지 않은 문항은 뒤로 (rate가 None)
    cards = sorted(
        data["rows"],
        key=lambda r: (r["rate"] if r["rate"] is not None else 101, r["no"]),
    )

    return render(request, "dvdexam/review.html", {
        "exam": exam,
        "cards_json": json.dumps(cards, ensure_ascii=False),
        "total": len(cards),
    })


@user_passes_test(_is_admin)
def scores(request, exam_id):
    """응시 결과 모아 보기. 화면은 아래 API로 실시간 갱신된다."""
    exam = get_object_or_404(Exam, id=exam_id)
    data = _scores_data(exam)

    return render(request, "dvdexam/scores.html", {
        "exam": exam,
        "rows": data["rows"],
        "stats": data["stats"],
    })


@user_passes_test(_is_admin)
def scores_api(request, exam_id):
    """응시 현황 JSON. 결과 화면이 주기적으로 불러 새로 그린다."""
    exam = get_object_or_404(Exam, id=exam_id)
    return JsonResponse(_scores_data(exam))


def _scores_data(exam):
    """응시자별 현황과 집계를 만든다."""
    total_q = exam.questions.count()
    attempts = (
        exam.attempts.select_related("user")
        .annotate(
            filled=Count("answers", filter=~Q(answers__given="")),
            hit=Count("answers", filter=Q(answers__is_correct=True)),
        )
        .order_by("-hit", "-filled", "started_at")
    )

    rows = []
    for a in attempts:
        answered = a.filled
        # 제출자는 전체 문항 기준, 응시 중인 사람은 푼 문항 기준으로 본다
        base = (a.total or total_q) if a.is_submitted else answered
        rows.append({
            "id": a.id,
            "name": a.user.first_name or a.user.username,
            "username": a.user.username,
            "submitted": a.is_submitted,
            "auto": a.auto_submitted,
            "correct": a.hit,
            "answered": answered,
            "total": a.total or total_q,
            "answer_percent": round(answered * 100 / total_q) if total_q else 0,
            # 푼 문제 중 몇 %를 맞혔는지 (제출 후에는 전체 기준 = 최종 점수)
            "percent": round(a.hit * 100 / base) if base else 0,
            "elapsed": a.elapsed_display,
            "elapsed_sec": a.elapsed_seconds,
            "submitted_at": timezone.localtime(a.submitted_at).strftime("%m/%d %H:%M")
                            if a.submitted_at else "",
            "started_at": timezone.localtime(a.started_at).strftime("%m/%d %H:%M"),
        })

    done = [r for r in rows if r["submitted"]]
    return {
        "rows": rows,
        "stats": {
            "taking": len(rows),
            "submitted": len(done),
            "in_progress": len(rows) - len(done),
            "average": round(sum(r["percent"] for r in done) / len(done)) if done else 0,
            "avg_elapsed": _format_seconds(
                round(sum(r["elapsed_sec"] for r in done) / len(done)) if done else 0
            ),
            "total_q": total_q,
        },
        "updated": timezone.localtime().strftime("%H:%M:%S"),
    }


def _format_seconds(seconds):
    """초를 '12분 34초' 형태로."""
    hours, rest = divmod(int(seconds), 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}시간 {minutes}분"
    if minutes:
        return f"{minutes}분 {secs}초"
    return f"{secs}초"
