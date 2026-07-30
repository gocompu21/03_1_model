import logging

from django.http import HttpResponse
from django.contrib.auth.models import User
from django.shortcuts import render
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .forms import SignUpForm, LoginForm
from .models import UserSession

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """클라이언트 IP 주소 추출"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def notify_admin_new_signup(user, request):
    """신규 가입 시 관리자에게 알림 메일 발송.

    메일 실패가 가입 자체를 막아서는 안 되므로 예외는 로그만 남기고 삼킨다.
    """
    to = getattr(settings, "ADMIN_NOTIFY_EMAIL", "")
    if not to:
        return

    joined = timezone.localtime(user.date_joined).strftime("%Y-%m-%d %H:%M")
    total = User.objects.count()
    body = (
        f"나무의사 합격반에 새 회원이 가입했습니다.\n\n"
        f"이름     : {user.first_name or '-'}\n"
        f"아이디   : {user.username}\n"
        f"이메일   : {user.email or '-'}\n"
        f"가입시각 : {joined}\n"
        f"IP       : {get_client_ip(request) or '-'}\n"
        f"기기정보 : {request.META.get('HTTP_USER_AGENT', '-')[:200]}\n\n"
        f"현재 총 회원수: {total}명\n"
        f"관리자 대시보드: https://studynamu.com/dashboard/\n"
    )

    try:
        send_mail(
            subject=f"[나무의사] 신규 가입: {user.first_name or user.username} ({user.username})",
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[to],
            fail_silently=False,
        )
    except Exception as e:
        logger.warning("신규 가입 알림 메일 발송 실패 (%s): %s", user.username, e)


def user_signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            
            # 세션 기록 생성 (기존 세션이 있으면 업데이트)
            if request.session.session_key:
                UserSession.objects.update_or_create(
                    session_key=request.session.session_key,
                    defaults={
                        'user': user,
                        'ip_address': get_client_ip(request),
                        'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
                        'logout_time': None,
                    }
                )

            # 관리자에게 신규 가입 알림
            notify_admin_new_signup(user, request)

            return redirect("main:index")
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
