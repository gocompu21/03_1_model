"""QR 출석 체크 기능.

관리자가 대시보드에서 당일자 QR을 띄우고, 학생이 휴대폰 카메라로
스캔하면 출석이 기록된다.

QR에 담기는 URL에는 날짜와 서명 토큰이 들어간다. 토큰은 SECRET_KEY로
만든 HMAC이라 임의로 날짜를 바꿔 다른 날 출석을 만들 수는 없다.
다만 당일 URL을 그대로 복사해 전달하면 현장에 없어도 출석이 되므로,
대리출석을 완전히 막지는 못한다.
"""

import hashlib
import hmac
import io

import qrcode
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
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


@staff_member_required
def admin_attendance(request):
    """관리자: 당일 QR 코드와 오늘 출석 현황을 보여준다."""
    today = timezone.localdate()
    date_str = today.isoformat()
    token = _make_token(date_str)

    check_url = request.build_absolute_uri(
        f"/accounts/attendance/check/?d={date_str}&t={token}"
    )

    records = (
        Attendance.objects.filter(date=today)
        .select_related("user")
        .order_by("checked_at")
    )

    return render(
        request,
        "accounts/admin_attendance.html",
        {
            "today": today,
            "check_url": check_url,
            "qr_src": f"/accounts/attendance/qr.png?d={date_str}&t={token}",
            "records": records,
            "record_count": records.count(),
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
