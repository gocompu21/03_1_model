"""QR 출석 체크 기능.

관리자가 대시보드에서 당일자 QR을 띄우고, 학생이 휴대폰 카메라로
스캔하면 출석이 기록된다.

QR에 담기는 URL에는 날짜와 서명 토큰이 들어간다. 토큰은 SECRET_KEY로
만든 HMAC이라 임의로 날짜를 바꿔 다른 날 출석을 만들 수는 없다.
다만 당일 URL을 그대로 복사해 전달하면 현장에 없어도 출석이 되므로,
대리출석을 완전히 막지는 못한다.
"""

import calendar
import hashlib
import hmac
import io
from datetime import date, datetime, timedelta

import qrcode
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Max
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import Attendance
from .views import get_client_ip


def _make_token(date_str):
    """날짜 문자열에 대한 서명 토큰 생성 (앞 16자만 사용)."""
    msg = f"attendance:{date_str}".encode()
    key = settings.SECRET_KEY.encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()[:16]


def _today_str():
    return timezone.localdate().isoformat()


def check_token(date_str, token):
    """토큰이 해당 날짜에 대해 유효한지 확인 (타이밍 공격 방지 비교)."""
    return hmac.compare_digest(_make_token(date_str), token or "")


def _parse_date(value, default):
    """YYYY-MM-DD 문자열을 date로 변환. 형식이 틀리면 default 반환."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return default


@staff_member_required
def admin_attendance(request):
    """관리자: QR 코드 + 선택한 날짜의 출석 현황.

    ?date=YYYY-MM-DD 로 과거 날짜를 조회할 수 있다. QR은 오늘 날짜만
    유효하므로, 과거 날짜를 볼 때는 QR을 숨기고 명단만 보여준다.
    """
    today = timezone.localdate()
    view_date = _parse_date(request.GET.get("date"), today)
    is_today = view_date == today

    date_str = today.isoformat()
    token = _make_token(date_str)
    check_url = request.build_absolute_uri(
        f"/accounts/attendance/check/?d={date_str}&t={token}"
    )

    records = (
        Attendance.objects.filter(date=view_date)
        .select_related("user")
        .order_by("checked_at")
    )

    # 해당 날짜에 출석하지 않은 사용자 (수동 추가 후보)
    attended_ids = records.values_list("user_id", flat=True)
    absentees = (
        User.objects.filter(is_active=True)
        .exclude(id__in=attended_ids)
        .order_by("first_name", "username")
    )

    return render(
        request,
        "accounts/admin_attendance.html",
        {
            "today": today,
            "view_date": view_date,
            "is_today": is_today,
            "prev_date": view_date - timedelta(days=1),
            "next_date": view_date + timedelta(days=1),
            "check_url": check_url,
            "qr_src": f"/accounts/attendance/qr.png?d={date_str}&t={token}",
            "records": records,
            "record_count": records.count(),
            "absentees": absentees,
            "absentee_count": absentees.count(),
        },
    )


@staff_member_required
def attendance_add(request):
    """관리자: 특정 사용자를 특정 날짜에 수동 출석 처리."""
    if request.method != "POST":
        return redirect("accounts:admin_attendance")

    user_id = request.POST.get("user_id")
    date_str = request.POST.get("date", "")
    view_date = _parse_date(date_str, timezone.localdate())

    user = User.objects.filter(id=user_id).first()
    if not user:
        messages.error(request, "사용자를 찾을 수 없습니다.")
    else:
        _, created = Attendance.objects.get_or_create(
            user=user,
            date=view_date,
            defaults={
                "ip_address": get_client_ip(request),
                "user_agent": "관리자 수동 등록",
            },
        )
        name = user.first_name or user.username
        if created:
            messages.success(request, f"{name} 님을 {view_date} 출석 처리했습니다.")
        else:
            messages.info(request, f"{name} 님은 이미 출석 상태입니다.")

    return redirect(f"{reverse('accounts:admin_attendance')}?date={view_date}")


@staff_member_required
def attendance_delete(request):
    """관리자: 출석 기록 삭제."""
    if request.method != "POST":
        return redirect("accounts:admin_attendance")

    record = Attendance.objects.filter(id=request.POST.get("record_id")).select_related("user").first()
    view_date = timezone.localdate()

    if not record:
        messages.error(request, "출석 기록을 찾을 수 없습니다.")
    else:
        view_date = record.date
        name = record.user.first_name or record.user.username
        record.delete()
        messages.success(request, f"{name} 님의 {view_date} 출석을 취소했습니다.")

    return redirect(f"{reverse('accounts:admin_attendance')}?date={view_date}")


@staff_member_required
def attendance_stats(request):
    """관리자: 학생별 누적 출석 통계."""
    stats = (
        User.objects.filter(is_active=True)
        .annotate(
            attend_count=Count("attendances"),
            last_attend=Max("attendances__date"),
        )
        .order_by("-attend_count", "first_name", "username")
    )

    # order_by() 필수. Meta.ordering의 checked_at이 DISTINCT에 딸려 들어가면
    # 날짜 수가 아니라 출석 기록 건수가 세어진다
    total_days = Attendance.objects.order_by().values("date").distinct().count()

    return render(
        request,
        "accounts/attendance_stats.html",
        {
            "stats": stats,
            "total_days": total_days,
            "today": timezone.localdate(),
        },
    )


@staff_member_required
def attendance_monthly(request):
    """관리자: 월별 출석부 (학생 × 날짜 교차표)."""
    today = timezone.localdate()
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
        if not 1 <= month <= 12:
            raise ValueError
    except (TypeError, ValueError):
        year, month = today.year, today.month

    days_in_month = calendar.monthrange(year, month)[1]
    first_day = date(year, month, 1)
    last_day = date(year, month, days_in_month)

    # 이 달에 출석 기록이 있는 날짜만 열로 표시 (빈 날 제외해 표를 좁게 유지)
    #
    # order_by()로 Meta.ordering을 반드시 걷어낸다. 기본 정렬에 checked_at이
    # 들어 있어 그대로 두면 DISTINCT에 checked_at이 딸려 들어가고, 체크 시각은
    # 사람마다 달라 같은 날이 출석 인원 수만큼 열로 반복된다
    active_days = sorted(
        Attendance.objects.filter(date__range=(first_day, last_day))
        .order_by()
        .values_list("date", flat=True)
        .distinct()
    )

    records = Attendance.objects.filter(date__range=(first_day, last_day)).values_list(
        "user_id", "date"
    )
    attended = set(records)

    users = (
        User.objects.filter(is_active=True)
        .order_by("first_name", "username")
    )

    rows = []
    for u in users:
        cells = [{"date": d, "present": (u.id, d) in attended} for d in active_days]
        present_count = sum(1 for c in cells if c["present"])
        # 이 달에 아무 출석도 없는 사용자는 표에서 제외
        if present_count:
            rows.append({"user": u, "cells": cells, "count": present_count})

    # 일자별 출석 인원. 표에 실제로 그린 행을 세어야 열 합계와 눈으로 맞는다
    # (탈퇴·비활성 사용자의 기록은 행이 없으니 합계에도 넣지 않는다)
    day_totals = [
        {
            "date": d,
            "count": sum(1 for r in rows if r["cells"][i]["present"]),
        }
        for i, d in enumerate(active_days)
    ]
    grand_total = sum(t["count"] for t in day_totals)

    prev_month = first_day - timedelta(days=1)
    next_month = last_day + timedelta(days=1)

    return render(
        request,
        "accounts/attendance_monthly.html",
        {
            "year": year,
            "month": month,
            "active_days": active_days,
            "rows": rows,
            "day_totals": day_totals,
            "grand_total": grand_total,
            "prev_year": prev_month.year,
            "prev_month": prev_month.month,
            "next_year": next_month.year,
            "next_month": next_month.month,
            "today": today,
        },
    )


@staff_member_required
def attendance_qr_png(request):
    """QR 코드 PNG 이미지를 생성해 반환한다."""
    date_str = request.GET.get("d", "")
    token = request.GET.get("t", "")

    if not check_token(date_str, token):
        return HttpResponse("invalid token", status=400)

    url = request.build_absolute_uri(
        f"/accounts/attendance/check/?d={date_str}&t={token}"
    )

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1b4332", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")

    response = HttpResponse(buf.getvalue(), content_type="image/png")
    response["Cache-Control"] = "no-store"
    return response


@login_required
def attendance_check(request):
    """학생: QR 스캔으로 열리는 출석 처리 페이지."""
    date_str = request.GET.get("d", "")
    token = request.GET.get("t", "")
    today_str = _today_str()

    # 서명이 틀렸거나 오늘 날짜가 아니면 거부
    if not check_token(date_str, token):
        status = "invalid"
    elif date_str != today_str:
        status = "expired"
    else:
        _, created = Attendance.objects.get_or_create(
            user=request.user,
            date=timezone.localdate(),
            defaults={
                "ip_address": get_client_ip(request),
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:500],
            },
        )
        status = "success" if created else "already"

    record = Attendance.objects.filter(
        user=request.user, date=timezone.localdate()
    ).first()

    return render(
        request,
        "accounts/attendance_result.html",
        {
            "status": status,
            "record": record,
            "today": timezone.localdate(),
        },
    )


@login_required
def my_attendance(request):
    """학생: 마이페이지 출석 메뉴 - 본인 출석 이력."""
    records = Attendance.objects.filter(user=request.user).order_by("-date")
    today = timezone.localdate()

    return render(
        request,
        "accounts/my_attendance.html",
        {
            "records": records[:60],
            "total_count": records.count(),
            "checked_today": records.filter(date=today).exists(),
            "today": today,
        },
    )
