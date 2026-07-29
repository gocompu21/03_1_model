from django.shortcuts import redirect
from django.contrib import messages


def csrf_failure(request, reason=""):
    messages.error(request, "세션이 만료되었습니다. 다시 로그인해 주세요.")
    return redirect("accounts:user_login")
