"""AI 기초 설문 — 누구나 답하고, 관리자(staff)만 통계를 본다."""

import csv
from collections import Counter

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .models import (
    AGE_CHOICES, DEVICE_CHOICES, FREQUENCY_CHOICES, LEVELS, PAID_CHOICES, QUIZ,
    SELF_LEVELS, TERM_LEVELS, TERMS, TOOL_CHOICES, USE_CHOICES, WORRY_CHOICES,
    PollResponse,
)


def _is_admin(user):
    return user.is_authenticated and user.is_staff


manager_required = user_passes_test(_is_admin, login_url="/accounts/login/")


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _form_context(data=None, errors=None):
    data = data or {}
    return {
        "data": data,
        # 템플릿에서 term_<key>·q1 값을 꺼내기 어려워 고른 값을 함께 넘긴다
        "term_rows": [(k, label, data.get(f"term_{k}", "")) for k, label in TERMS],
        "quiz_rows": [(k, text, data.get(k, "")) for k, text, _ in QUIZ],
        "errors": errors or [],
        "age_choices": AGE_CHOICES,
        "device_choices": DEVICE_CHOICES,
        "tool_choices": TOOL_CHOICES,
        "frequency_choices": FREQUENCY_CHOICES,
        "use_choices": USE_CHOICES,
        "paid_choices": PAID_CHOICES,
        "terms": TERMS,
        "term_levels": TERM_LEVELS,
        "quiz": QUIZ,
        "self_levels": SELF_LEVELS,
        "worry_choices": WORRY_CHOICES,
    }


def _pick(post, key, choices):
    value = post.get(key, "")
    return value if value in dict(choices) else ""


def _pick_many(post, key, choices):
    allowed = dict(choices)
    return [v for v in post.getlist(key) if v in allowed]


# ---------------------------------------------------------------- 설문

@never_cache
def index(request):
    if request.method != "POST":
        return render(request, "poll/form.html", _form_context())

    post = request.POST
    name = post.get("name", "").strip()[:50]
    tools = _pick_many(post, "tools", TOOL_CHOICES)
    if "none" in tools:
        tools = ["none"]
    terms = {k: post.get(f"term_{k}") for k, _ in TERMS}
    quiz = {k: post.get(k) for k, _, _ in QUIZ}

    fields = {
        "age_group": _pick(post, "age_group", AGE_CHOICES),
        "device_level": _pick(post, "device_level", DEVICE_CHOICES),
        "frequency": _pick(post, "frequency", FREQUENCY_CHOICES),
        "paid": _pick(post, "paid", PAID_CHOICES),
        "self_level": _pick(post, "self_level", SELF_LEVELS),
    }

    errors = []
    if not name:
        errors.append("이름을 적어 주세요.")
    labels = {"age_group": "연령대", "device_level": "컴퓨터·스마트폰 활용",
              "frequency": "사용 빈도", "paid": "유료 구독",
              "self_level": "스스로 생각하는 수준"}
    for key, label in labels.items():
        if not fields[key]:
            errors.append(f"'{label}'을(를) 골라 주세요.")
    if not tools:
        errors.append("'써 본 AI'를 하나 이상 골라 주세요.")
    if any(v not in ("0", "1", "2") for v in terms.values()):
        errors.append("용어 이해도를 낱말마다 골라 주세요.")
    if any(v not in ("O", "X") for v in quiz.values()):
        errors.append("OX 문제에 모두 답해 주세요.")

    if errors:
        data = dict(post.lists())
        data = {k: (v if len(v) > 1 or k in ("tools", "uses", "worries") else v[0])
                for k, v in data.items()}
        return render(request, "poll/form.html", _form_context(data, errors))

    resp = PollResponse.objects.filter(name=name).first() or PollResponse(name=name)
    for key, value in fields.items():
        setattr(resp, key, value)
    resp.tools = tools
    resp.uses = _pick_many(post, "uses", USE_CHOICES)
    resp.terms = terms
    resp.quiz = quiz
    resp.worries = _pick_many(post, "worries", WORRY_CHOICES)
    resp.want_to_learn = post.get("want_to_learn", "").strip()[:2000]
    resp.ip = _client_ip(request)
    resp.score = resp.compute_score()
    resp.save()

    request.session["poll_name"] = name
    return redirect("poll:done")


def done(request):
    return render(request, "poll/done.html", {"name": request.session.get("poll_name", "")})


# ---------------------------------------------------------------- 관리자

def _distribution(values, choices, total):
    """[(라벨, 수, 비율%)] — 보기 순서대로."""
    counter = Counter(values)
    return [
        (label, counter.get(key, 0), round(counter.get(key, 0) * 100 / total) if total else 0)
        for key, label in choices
    ]


@manager_required
@never_cache
def manage(request):
    responses = list(PollResponse.objects.all())
    total = len(responses)

    single = [
        ("연령대", "age_group", AGE_CHOICES),
        ("컴퓨터·스마트폰 활용", "device_level", DEVICE_CHOICES),
        ("AI 사용 빈도", "frequency", FREQUENCY_CHOICES),
        ("유료 구독", "paid", PAID_CHOICES),
        ("스스로 생각하는 수준", "self_level", SELF_LEVELS),
    ]
    multi = [
        ("써 본 AI", "tools", TOOL_CHOICES),
        ("주로 하는 일", "uses", USE_CHOICES),
        ("어렵거나 걱정되는 점", "worries", WORRY_CHOICES),
    ]

    charts = []
    for title, field, choices in single:
        rows = _distribution([getattr(r, field) for r in responses], choices, total)
        charts.append({"title": title, "rows": rows, "multi": False})
    for title, field, choices in multi:
        values = [v for r in responses for v in getattr(r, field)]
        rows = _distribution(values, choices, total)
        rows.sort(key=lambda x: -x[1])
        charts.append({"title": title, "rows": rows, "multi": True})

    term_rows = []
    for key, label in TERMS:
        counts = Counter(r.terms.get(key) for r in responses)
        cells = [(counts.get(lv, 0), round(counts.get(lv, 0) * 100 / total) if total else 0)
                 for lv, _ in TERM_LEVELS]
        term_rows.append((label, cells))

    quiz_rows = []
    for key, text, answer in QUIZ:
        right = sum(1 for r in responses if r.quiz.get(key) == answer)
        quiz_rows.append((text, answer, right, round(right * 100 / total) if total else 0))

    level_counts = Counter(r.level for r in responses)
    levels = [(name, level_counts.get(name, 0),
               round(level_counts.get(name, 0) * 100 / total) if total else 0)
              for _, name in LEVELS]

    tool_labels = dict(TOOL_CHOICES)
    for r in responses:
        r.tool_names = ", ".join(tool_labels.get(t, t) for t in r.tools)

    today = timezone.localdate()
    context = {
        "total": total,
        "today_count": sum(1 for r in responses if timezone.localdate(r.updated_at) == today),
        "last": responses[0] if responses else None,
        "avg_score": round(sum(r.score for r in responses) / total) if total else 0,
        "levels": levels,
        "charts": charts,
        "term_levels": TERM_LEVELS,
        "term_rows": term_rows,
        "quiz_rows": quiz_rows,
        "responses": responses,
        "wishes": [r for r in responses if r.want_to_learn],
    }
    return render(request, "poll/manage.html", context)


@manager_required
def export_csv(request):
    labels = {
        "tools": dict(TOOL_CHOICES), "uses": dict(USE_CHOICES),
        "worries": dict(WORRY_CHOICES),
    }
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    stamp = timezone.localtime().strftime("%Y%m%d_%H%M")
    response["Content-Disposition"] = f'attachment; filename="ai_poll_{stamp}.csv"'
    response.write("﻿")  # 엑셀에서 한글이 깨지지 않게
    writer = csv.writer(response)
    writer.writerow(
        ["이름", "연령대", "기기 활용", "써 본 AI", "사용 빈도", "주로 하는 일",
         "유료 구독"]
        + [label for _, label in TERMS]
        + [f"OX{i + 1}" for i in range(len(QUIZ))]
        + ["자기평가", "걱정되는 점", "배우고 싶은 것", "점수", "수준", "제출 시각"]
    )
    term_labels = dict(TERM_LEVELS)
    for r in PollResponse.objects.all():
        writer.writerow(
            [r.name, r.get_age_group_display(), r.get_device_level_display(),
             ", ".join(labels["tools"].get(v, v) for v in r.tools),
             r.get_frequency_display(),
             ", ".join(labels["uses"].get(v, v) for v in r.uses),
             r.get_paid_display()]
            + [term_labels.get(r.terms.get(k), "") for k, _ in TERMS]
            + [r.quiz.get(k, "") for k, _, _ in QUIZ]
            + [r.self_level,
               ", ".join(labels["worries"].get(v, v) for v in r.worries),
               r.want_to_learn, r.score, r.level,
               timezone.localtime(r.updated_at).strftime("%Y-%m-%d %H:%M")]
        )
    return response


@manager_required
@require_POST
def delete(request, pk):
    resp = get_object_or_404(PollResponse, pk=pk)
    messages.success(request, f"'{resp.name}' 응답을 지웠습니다.")
    resp.delete()
    return redirect("poll:manage")
