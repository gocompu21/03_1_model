import logging

from django.http import HttpResponse
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .forms import SignUpForm, LoginForm
from .models import SignupApproval, UserSession

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """클라이언트 IP 주소 추출"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def notify_admin_new_signup(user, request, approval=None):
    """신규 가입 시 관리자에게 승인 요청 메일 발송.

    메일 실패가 가입 자체를 막아서는 안 되므로 예외는 로그만 남기고 삼킨다.
    """
    to = getattr(settings, "ADMIN_NOTIFY_EMAIL", "")
    if not to:
        return

    joined = timezone.localtime(user.date_joined).strftime("%Y-%m-%d %H:%M")
    waiting = SignupApproval.objects.filter(status="pending").count()
    base = getattr(settings, "SITE_URL", "https://studynamu.com").rstrip("/")

    body = (
        f"나무의사 합격반에 가입 신청이 접수되었습니다.\n"
        f"승인해야 로그인할 수 있습니다.\n\n"
        f"이름     : {user.first_name or '-'}\n"
        f"아이디   : {user.username}\n"
        f"이메일   : {user.email or '-'}\n"
        f"신청시각 : {joined}\n"
        f"IP       : {get_client_ip(request) or '-'}\n"
        f"기기정보 : {request.META.get('HTTP_USER_AGENT', '-')[:200]}\n\n"
    )

    if approval:
        body += (
            f"■ 승인하기\n{base}/accounts/approve/{approval.token}/\n\n"
            f"■ 거부하기\n{base}/accounts/reject/{approval.token}/\n\n"
        )

    body += (
        f"대기 중인 신청: {waiting}건\n"
        f"승인 관리: {base}/accounts/approvals/\n"
    )

    try:
        send_mail(
            subject=f"[나무의사] 가입 승인 요청: {user.first_name or user.username} ({user.username})",
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[to],
            fail_silently=False,
        )
    except Exception as e:
        logger.warning("가입 승인 요청 메일 발송 실패 (%s): %s", user.username, e)


def _is_admin(user):
    return user.is_authenticated and user.is_staff


def approve_signup(request, token):
    """메일 링크로 승인. 토큰만 알면 되므로 로그인은 요구하지 않는다."""
    approval = get_object_or_404(SignupApproval, token=token)
    already = approval.status != "pending"
    if not already:
        approval.approve(by="메일 링크")
        _notify_user_approved(approval.user)
    return render(request, "accounts/approval_result.html", {
        "approval": approval, "action": "approve", "already": already,
    })


def reject_signup(request, token):
    """메일 링크로 거부."""
    approval = get_object_or_404(SignupApproval, token=token)
    already = approval.status != "pending"
    if not already:
        approval.reject(by="메일 링크")
    return render(request, "accounts/approval_result.html", {
        "approval": approval, "action": "reject", "already": already,
    })


@user_passes_test(_is_admin)
def approval_list(request):
    """승인 관리 페이지."""
    if request.method == "POST":
        approval = SignupApproval.objects.filter(id=request.POST.get("id")).first()
        action = request.POST.get("action")
        if approval and approval.status == "pending":
            if action == "approve":
                approval.approve(by=request.user.username)
                _notify_user_approved(approval.user)
            elif action == "reject":
                approval.reject(by=request.user.username)
        return redirect("accounts:approval_list")

    approvals = SignupApproval.objects.select_related("user")
    return render(request, "accounts/approval_list.html", {
        "pending": approvals.filter(status="pending"),
        "decided": approvals.exclude(status="pending")[:30],
    })


def _notify_user_approved(user):
    """승인되었음을 가입자에게 알린다."""
    if not user.email:
        return
    base = getattr(settings, "SITE_URL", "https://studynamu.com").rstrip("/")
    try:
        send_mail(
            subject="[나무의사 합격반] 가입이 승인되었습니다",
            message=(
                f"{user.first_name or user.username}님, 가입이 승인되었습니다.\n\n"
                f"아래 주소에서 로그인해 주세요.\n{base}/accounts/login/\n\n"
                f"아이디: {user.username}\n"
            ),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as e:
        logger.warning("승인 안내 메일 발송 실패 (%s): %s", user.username, e)


def user_signup(request):
    """가입 신청. 관리자가 승인해야 로그인할 수 있다."""
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # 승인 전까지 로그인 불가
            user.save()

            approval = SignupApproval.objects.create(
                user=user,
                token=SignupApproval.new_token(),
                ip_address=get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
            )

            # 관리자에게 승인 요청 메일
            notify_admin_new_signup(user, request, approval)

            return render(request, "accounts/signup_pending.html", {"user_obj": user})
    else:
        form = SignUpForm()
    return render(request, "accounts/signup.html", {"form": form})


# 로그인시 필요 로직이 있으면 담는다.
def user_login(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            # 세션 기록 생성 (기존 세션이 있으면 업데이트)
            if request.session.session_key:
                UserSession.objects.update_or_create(
                    session_key=request.session.session_key,
                    defaults={
                        'user': user,
                        'ip_address': get_client_ip(request),
                        'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
                        'logout_time': None,  # 새 로그인이므로 logout_time 초기화
                    }
                )

            # Check for 'next' parameter
            next_url = request.POST.get("next")
            if next_url:
                return redirect(next_url)

            return redirect("main:index")

        # 승인 대기 등 로그인 거절 사유를 화면에 보여준다
        error = " ".join(form.non_field_errors()) or "아이디 또는 비밀번호를 확인해 주세요."
        return render(request, "accounts/login.html", {"form": form, "error": error})
    else:
        form = LoginForm()

    # Pass 'next' to context if strictly needed, or let template access request.GET
    return render(request, "accounts/login.html", {"form": form})


def user_logout(request):
    # 세션 기록 종료
    if request.user.is_authenticated and request.session.session_key:
        UserSession.objects.filter(
            user=request.user,
            session_key=request.session.session_key,
            logout_time__isnull=True
        ).update(logout_time=timezone.now())
    
    logout(request)
    return redirect("main:index")


def password_reset_request(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")

        try:
            user = User.objects.get(first_name=name, email=email)

            # Generate random 8-char password
            import random
            import string

            length = 8
            chars = string.ascii_letters + string.digits
            new_password = "".join(random.choice(chars) for _ in range(length))

            # Set password
            user.set_password(new_password)
            user.save()

            # Send Email
            from django.core.mail import send_mail

            subject = "[나무의사] 비밀번호가 초기화되었습니다."
            message = (
                f"안녕하세요, {user.first_name}님.\n\n"
                f"요청하신 비밀번호 초기화가 완료되었습니다.\n"
                f"--------------------------------\n"
                f"아이디: {user.username}\n"
                f"임시 비밀번호: {new_password}\n"
                f"--------------------------------\n\n"
                f"로그인 후 반드시 비밀번호를 변경해 주세요."
            )

            send_mail(
                subject,
                message,
                "admin@namudoctor.com",  # From email
                [user.email],
                fail_silently=False,
            )

            messages.success(request, "입력하신 이메일로 임시 비밀번호를 전송했습니다.")
            return redirect("accounts:user_login")

        except User.DoesNotExist:
            messages.error(request, "일치하는 회원 정보를 찾을 수 없습니다.")

    return render(request, "accounts/password_reset.html")


from django.http import JsonResponse

@login_required
def session_heartbeat(request):
    """iPad에서 세션 활동을 주기적으로 업데이트하기 위한 heartbeat 엔드포인트"""
    if request.session.session_key:
        try:
            session = UserSession.objects.filter(
                user=request.user,
                session_key=request.session.session_key,
                logout_time__isnull=True
            ).first()
            
            if session:
                session.save(update_fields=['last_activity'])
                return JsonResponse({"success": True})
            else:
                # 세션 기록이 없는 경우 (DB 삭제 등) 복구 시도
                UserSession.objects.create(
                    user=request.user,
                    session_key=request.session.session_key,
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                    logout_time=None
                )
                return JsonResponse({"success": True, "info": "Session recovered"})
        except Exception:
            pass
    
    return JsonResponse({"success": False})
