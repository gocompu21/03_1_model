from django.http import HttpResponse
from django.contrib.auth.models import User
from django.shortcuts import render
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .forms import SignUpForm, LoginForm


def user_signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
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
