import csv
from collections import Counter

from django.contrib.auth.decorators import user_passes_test
from django.db.models import Avg
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    AI_TOOL_CHOICES,
    CONCERN_CHOICES,
    FREQUENCY_CHOICES,
    LEVEL_NAMES,
    OX_QUESTIONS,
    SELF_LEVEL_CHOICES,
    SKILL_CHOICES,
    SUBSCRIPTION_CHOICES,
    TERM_LEVELS,
    TERMS,
    USE_CHOICES,
    PollResponse,
)

staff_required = user_passes_test(lambda u: u.is_active and u.is_staff, login_url="/accounts/login/")


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _keys(choices):
    return {k for k, _ in choices}


def _form_context(data, errors):
    return {
        "data": data,
        "errors": errors,
        "skill_choices": SKILL_CHOICES,
        "ai_tool_choices": AI_TOOL_CHOICES,
        "frequency_choices": FREQUENCY_CHOICES,
        "use_choices": USE_CHOICES,
        "subscription_choices": SUBSCRIPTION_CHOICES,
        "terms": [(k, label, data.get("terms", {}).get(k, "")) for k, label in TERMS],
        "term_levels": TERM_LEVELS,
        "ox_questions": [(k, text, data.get("ox", {}).get(k, "")) for k, text, _ in OX_QUESTIONS],
        "self_level_choices": SELF_LEVEL_CHOICES,
        "concern_choices": CONCERN_CHOICES,
    }


def survey(request):
    data = {"ai_tools": [], "uses": [], "concerns": [], "terms": {}, "ox": {}}
    errors = []
    if request.method == "POST":
        p = request.POST
        data = {
            "name": p.get("name", "").strip()[:50],
            "age": p.get("age", "").strip(),
            "skill": p.get("skill", ""),
            "ai_tools": [v for v in p.getlist("ai_tools") if v in _keys(AI_TOOL_CHOICES)],
            "frequency": p.get("frequency", ""),
            "uses": [v for v in p.getlist("uses") if v in _keys(USE_CHOICES)],
            "subscription": p.get("subscription", ""),
            "terms": {k: p.get(f"term_{k}", "") for k, _ in TERMS},
            "ox": {k: p.get(f"ox_{k}", "") for k, _, _ in OX_QUESTIONS},
            "self_level": p.get("self_level", ""),
            "concerns": [v for v in p.getlist("concerns") if v in _keys(CONCERN_CHOICES)],
            "wish": p.get("wish", "").strip()[:1000],
        }
        if "none" in data["ai_tools"]:
            data["ai_tools"] = ["none"]

        if not data["name"]:
            errors.append("1. 이름을 적어 주세요.")
        try:
            age = int(data["age"])
            if not 10 <= age <= 99:
                raise ValueError
        except ValueError:
            errors.append("2. 나이를 숫자로 적어 주세요 (10~99).")
        if data["skill"] not in _keys(SKILL_CHOICES):
            errors.append("3. 컴퓨터·스마트폰 활용 정도를 골라 주세요.")
        if not data["ai_tools"]:
            errors.append("4. 써 본 AI를 골라 주세요 (없으면 '써 본 적 없음').")
        if data["frequency"] not in _keys(FREQUENCY_CHOICES):
            errors.append("5. 사용 빈도를 골라 주세요.")
        if data["subscription"] not in _keys(SUBSCRIPTION_CHOICES):
            errors.append("7. 유료 구독 여부를 골라 주세요.")
        if any(v not in _keys(TERM_LEVELS) for v in data["terms"].values()):
            errors.append("8. 용어마다 하나씩 골라 주세요.")
        if any(v not in ("O", "X") for v in data["ox"].values()):
            errors.append("9. O 또는 X를 골라 주세요.")
        if data["self_level"] not in _keys(SELF_LEVEL_CHOICES):
            errors.append("10. 스스로 생각하는 AI 수준을 골라 주세요.")

        if not errors:
            obj, _ = PollResponse.objects.update_or_create(
                name=data["name"],
                defaults={
                    "age": int(data["age"]),
                    "skill": data["skill"],
                    "ai_tools": data["ai_tools"],
                    "frequency": data["frequency"],
                    "uses": data["uses"],
                    "subscription": data["subscription"],
                    "terms": data["terms"],
                    "ox": data["ox"],
                    "self_level": int(data["self_level"]),
                    "concerns": data["concerns"],
                    "wish": data["wish"],
                    "ip": _client_ip(request),
                },
            )
            request.session["poll_name"] = obj.name
            return redirect("poll:done")
    return render(request, "poll/survey.html", _form_context(data, errors))


def done(request):
    name = request.session.get("poll_name")
    if not name:
        return redirect("poll:survey")
    return render(request, "poll/done.html", {"name": name})


def _bars(counter, choices, total):
    rows = []
    for key, label in choices:
        n = counter.get(key, 0)
        rows.append({"label": label, "count": n, "pct": round(n * 100 / total) if total else 0})
    return rows


def _age_group(age):
    if age < 30:
        return "20대 이하"
    if age >= 70:
        return "70대 이상"
    return f"{age // 10 * 10}대"


AGE_GROUPS = ["20대 이하", "30대", "40대", "50대", "60대", "70대 이상"]


@staff_required
def manage(request):
    responses = list(PollResponse.objects.all())
    total = len(responses)
    today = timezone.localdate()
    agg = PollResponse.objects.aggregate(avg_age=Avg("age"), avg_score=Avg("score"))

    def single(field, choices):
        return _bars(Counter(getattr(r, field) for r in responses), choices, total)

    def multi(field, choices):
        c = Counter()
        for r in responses:
            c.update(set(getattr(r, field) or []))
        return _bars(c, choices, total)

    level_counter = Counter(r.level for r in responses)
    age_counter = Counter(_age_group(r.age) for r in responses)

    term_rows = []
    for key, label in TERMS:
        c = Counter(str((r.terms or {}).get(key, "")) for r in responses)
        cells = [{"count": c.get(lv, 0), "pct": round(c.get(lv, 0) * 100 / total) if total else 0} for lv, _ in TERM_LEVELS]
        term_rows.append({"label": label, "cells": cells})

    ox_rows = []
    for key, text, answer in OX_QUESTIONS:
        right = sum(1 for r in responses if (r.ox or {}).get(key) == answer)
        ox_rows.append({"text": text, "answer": answer, "right": right,
                        "pct": round(right * 100 / total) if total else 0})

    ctx = {
        "total": total,
        "today_count": sum(1 for r in responses if timezone.localtime(r.submitted_at).date() == today),
        "avg_age": round(agg["avg_age"], 1) if agg["avg_age"] is not None else None,
        "avg_score": round(agg["avg_score"], 1) if agg["avg_score"] is not None else None,
        "last_at": responses[0].submitted_at if responses else None,
        "level_bars": _bars(level_counter, [(n, n) for n in LEVEL_NAMES], total),
        "age_bars": _bars(age_counter, [(g, g) for g in AGE_GROUPS], total),
        "sections": [
            ("3. 컴퓨터·스마트폰 활용", single("skill", SKILL_CHOICES)),
            ("4. 써 본 AI (복수)", multi("ai_tools", AI_TOOL_CHOICES)),
            ("5. 사용 빈도", single("frequency", FREQUENCY_CHOICES)),
            ("6. 주로 하는 일 (복수)", multi("uses", USE_CHOICES)),
            ("7. 유료 구독", single("subscription", SUBSCRIPTION_CHOICES)),
            ("10. 스스로 생각하는 AI 수준", _bars(Counter(str(r.self_level) for r in responses), SELF_LEVEL_CHOICES, total)),
            ("11. 어렵거나 걱정되는 점 (복수)", multi("concerns", CONCERN_CHOICES)),
        ],
        "term_levels": TERM_LEVELS,
        "term_rows": term_rows,
        "ox_rows": ox_rows,
        "wishes": [r for r in responses if r.wish],
        "responses": responses,
    }
    return render(request, "poll/manage.html", ctx)


def _labels(keys, choices):
    d = dict(choices)
    return ", ".join(d.get(k, k) for k in keys or [])


@staff_required
def export_csv(request):
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="ai_poll.csv"'
    resp.write("﻿")
    w = csv.writer(resp)
    term_labels = dict(TERM_LEVELS)
    w.writerow(["이름", "나이", "컴퓨터 활용", "써 본 AI", "빈도", "주로 하는 일", "유료 구독"]
               + [label for _, label in TERMS]
               + [text for _, text, _ in OX_QUESTIONS]
               + ["자기 평가", "걱정되는 점", "배우고 싶은 것", "점수", "수준", "제출 시각", "IP"])
    for r in PollResponse.objects.all():
        w.writerow([r.name, r.age, r.get_skill_display(), _labels(r.ai_tools, AI_TOOL_CHOICES),
                    r.get_frequency_display(), _labels(r.uses, USE_CHOICES), r.get_subscription_display()]
                   + [term_labels.get(str((r.terms or {}).get(k, "")), "") for k, _ in TERMS]
                   + [(r.ox or {}).get(k, "") for k, _, _ in OX_QUESTIONS]
                   + [r.self_level, _labels(r.concerns, CONCERN_CHOICES), r.wish, r.score, r.level,
                      timezone.localtime(r.submitted_at).strftime("%Y-%m-%d %H:%M"), r.ip or ""])
    return resp


@staff_required
@require_POST
def delete_response(request, pk):
    get_object_or_404(PollResponse, pk=pk).delete()
    return redirect("poll:manage")
