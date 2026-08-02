import json
import random

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from .models import TreeBookmark, TreeQuestion


@login_required
def memorize(request):
    """수목 암기. 코스 구분 없이 전체를 사진 -> 정보 순으로 넘겨본다."""
    base = TreeQuestion.objects.filter(course__is_active=True).select_related("course")
    total_all = base.count()

    marked_ids = set(
        TreeBookmark.objects.filter(user=request.user).values_list("question_id", flat=True)
    )

    scope = request.GET.get("scope", "all")
    if scope == "marked":
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
            # 수목은 정해진 정답 항목이 없어 설명을 줄 단위로 보여준다
            "lines": q.description_lines(),
            # 코스명에 수목명이 들어 있어(예: "01. 소철 ~ 노간주나무") 내려주지 않는다
        }
        for q in questions
    ]

    order = "sequence"
    if request.GET.get("order") == "random":
        random.shuffle(payload)
        order = "random"

    return render(request, "treeid/memorize.html", {
        "cards_json": json.dumps(payload, ensure_ascii=False),
        "total": len(payload),
        "order": order,
        "scope": scope,
        "marked_count": len(marked_ids),
        "total_all": total_all,
    })


@login_required
def bookmark(request):
    """관심 수목 등록/해제 API."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid json"}, status=400)

    question = TreeQuestion.objects.filter(id=body.get("question_id")).first()
    if not question:
        return JsonResponse({"error": "not found"}, status=404)

    if body.get("marked"):
        TreeBookmark.objects.get_or_create(user=request.user, question=question)
        marked = True
    else:
        TreeBookmark.objects.filter(user=request.user, question=question).delete()
        marked = False

    return JsonResponse({
        "ok": True,
        "marked": marked,
        "count": TreeBookmark.objects.filter(user=request.user).count(),
    })
