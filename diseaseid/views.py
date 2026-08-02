import json
import random

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from .models import DiseaseBookmark, DiseaseQuestion


@login_required
def memorize(request):
    """병해 암기. 코스 구분 없이 전체를 사진 -> 정보 순으로 넘겨본다."""
    base = DiseaseQuestion.objects.filter(course__is_active=True).select_related("course")
    total_all = base.count()

    marked_ids = set(
        DiseaseBookmark.objects.filter(user=request.user).values_list("question_id", flat=True)
    )

    scope = request.GET.get("scope", "all")
    if scope == "past":
        selected = base.filter(exam_stars__gt=0)
    elif scope == "marked":
        selected = base.filter(id__in=marked_ids)
    else:
        scope = "all"
        selected = base

    questions = list(selected.order_by("course__order", "order", "id"))

    payload = [
        {
            "id": q.id,
            "marked": q.id in marked_ids,
            "image": q.image.url,
            "name": q.name,
            "fields": [
                {"label": label, "value": value}
                for key, label, value in q.answer_fields()
                if key != "name"
            ],
            "course": q.course.name,
            "taxon": q.taxonomy,
            "stars": q.exam_stars,
            "exam": q.exam_note,
            # 채점 항목은 아니지만 함께 외우면 좋은 참고 정보
            "extra": [
                {"label": label, "value": value}
                for label, value in (("중간기주", q.alt_host),)
                if value
            ],
        }
        for q in questions
    ]

    order = "sequence"
    if request.GET.get("order") == "random":
        random.shuffle(payload)
        order = "random"

    return render(request, "diseaseid/memorize.html", {
        "cards_json": json.dumps(payload, ensure_ascii=False),
        "total": len(payload),
        "order": order,
        "scope": scope,
        "past_count": base.filter(exam_stars__gt=0).count(),
        "marked_count": len(marked_ids),
        "total_all": total_all,
    })


@login_required
def bookmark(request):
    """관심 병해 등록/해제 API."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid json"}, status=400)

    question = DiseaseQuestion.objects.filter(id=body.get("question_id")).first()
    if not question:
        return JsonResponse({"error": "not found"}, status=404)

    if body.get("marked"):
        DiseaseBookmark.objects.get_or_create(user=request.user, question=question)
        marked = True
    else:
        DiseaseBookmark.objects.filter(user=request.user, question=question).delete()
        marked = False

    return JsonResponse({
        "ok": True,
        "marked": marked,
        "count": DiseaseBookmark.objects.filter(user=request.user).count(),
    })
