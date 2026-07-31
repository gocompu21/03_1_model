import json
import random

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import PestAttempt, PestCourse, PestQuestion


@login_required
def index(request):
    """코스 목록과 내 최고 기록."""
    # annotate가 GROUP BY를 만들면 Meta.ordering이 적용되지 않으므로 직접 정렬한다
    courses = (
        PestCourse.objects.filter(is_active=True)
        .annotate(q_count=Count("questions"))
        .filter(q_count__gt=0)
        .order_by("order", "id")
    )

    best = {
        row["course_id"]: row["best"]
        for row in PestAttempt.objects.filter(
            user=request.user, finished_at__isnull=False
        )
        .values("course_id")
        .annotate(best=Max("correct_count"))
    }

    for c in courses:
        c.my_best = best.get(c.id)

    return render(request, "pestid/index.html", {"courses": courses})


@login_required
def memorize(request):
    """해충 암기. 코스 구분 없이 전체 해충을 사진 -> 정보 순으로 넘겨본다.

    채점이 없으므로 정답 정보를 그대로 내려준다.
    """
    base = PestQuestion.objects.filter(course__is_active=True).select_related("course")
    total_all = base.count()

    # 시험이 가까울 때는 기출 종만 추려 보는 편이 효율적이다
    only_past = request.GET.get("scope") == "past"
    questions = list(
        (base.filter(exam_stars__gt=0) if only_past else base).order_by(
            "course__order", "order", "id"
        )
    )

    payload = [
        {
            "image": q.image.url,
            "name": q.name,
            # 쉼표 뒤는 같은 뜻의 별해라 사진 위에서는 대표값만 보여준다
            "fields": [
                {"label": label, "value": value.split(",")[0].strip()}
                for key, label, value in q.answer_fields()
                if key != "name"
            ],
            "course": q.course.name,
            "taxon": " ".join(x for x in (q.taxon_order, q.taxon_family) if x),
            "stars": q.exam_stars,
            "exam": q.exam_note,
        }
        for q in questions
    ]

    order = "sequence"
    if request.GET.get("order") == "random":
        random.shuffle(payload)
        order = "random"

    return render(request, "pestid/memorize.html", {
        "cards_json": json.dumps(payload, ensure_ascii=False),
        "total": len(payload),
        "order": order,
        "scope": "past" if only_past else "all",
        "past_count": base.filter(exam_stars__gt=0).count(),
        "total_all": total_all,
    })


@login_required
def play(request, course_id):
    """퀴즈 화면. 문제 데이터를 JSON으로 함께 내려준다.

    객관식 보기는 같은 코스의 다른 값에서 뽑는다. 후보가 부족하면
    해당 항목은 주관식으로 출제한다.
    """
    course = get_object_or_404(PestCourse, id=course_id, is_active=True)
    mode = request.GET.get("mode", "choice")
    if mode not in ("choice", "typing"):
        mode = "choice"

    questions = list(course.questions.all())
    if not questions:
        return render(request, "pestid/index.html", {
            "courses": PestCourse.objects.filter(is_active=True),
            "error": "이 코스에는 아직 문제가 없습니다.",
        })

    # 항목별 오답 후보 풀 (중복 제거)
    pools = {}
    for key in PestQuestion.FIELD_LABELS:
        values = {
            getattr(q, key).split(",")[0].strip()
            for q in questions
            if getattr(q, key, "").strip()
        }
        pools[key] = sorted(values)

    payload = []
    for q in questions:
        fields = []
        for key, label, correct in q.answer_fields():
            # 표시용 정답은 첫 번째 값, 실제 채점은 서버가 담당
            display = correct.split(",")[0].strip()
            item = {"key": key, "label": label}

            if mode == "choice":
                distractors = [v for v in pools[key] if v != display]
                random.shuffle(distractors)
                picked = distractors[:3]
                if len(picked) < 3:
                    # 보기를 채울 수 없으면 이 항목만 주관식으로
                    item["type"] = "typing"
                else:
                    options = picked + [display]
                    random.shuffle(options)
                    item["type"] = "choice"
                    item["options"] = options
            else:
                item["type"] = "typing"

            fields.append(item)

        payload.append({
            "id": q.id,
            "image": q.image.url,
            "fields": fields,
        })

    random.shuffle(payload)

    return render(request, "pestid/play.html", {
        "course": course,
        "mode": mode,
        "questions_json": json.dumps(payload, ensure_ascii=False),
        "total": len(payload),
    })


@login_required
def grade(request):
    """단일 항목 채점 API. 정답 판정은 서버에서만 한다."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid json"}, status=400)

    q = PestQuestion.objects.filter(id=body.get("question_id")).first()
    key = body.get("key", "")
    if not q or key not in PestQuestion.FIELD_LABELS:
        return JsonResponse({"error": "not found"}, status=404)

    return JsonResponse({
        "correct": q.is_correct(key, body.get("answer", "")),
        "answer": getattr(q, key, ""),
    })


@login_required
def finish(request):
    """도전 결과 저장."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid json"}, status=400)

    course = PestCourse.objects.filter(id=body.get("course_id")).first()
    if not course:
        return JsonResponse({"error": "course not found"}, status=404)

    mode = body.get("mode", "choice")
    if mode not in ("choice", "typing"):
        mode = "choice"

    try:
        total = int(body.get("total", 0))
        correct = int(body.get("correct", 0))
    except (TypeError, ValueError):
        return JsonResponse({"error": "invalid score"}, status=400)

    attempt = PestAttempt.objects.create(
        user=request.user,
        course=course,
        mode=mode,
        total_count=total,
        correct_count=correct,
        finished_at=timezone.now(),
    )

    return JsonResponse({
        "ok": True,
        "score": attempt.score_percent,
        "correct": attempt.correct_count,
        "total": attempt.total_count,
    })
