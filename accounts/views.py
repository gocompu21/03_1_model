from django.http import HttpResponse
from django.contrib.auth.models import User
from django.shortcuts import render
from django.contrib.auth import login, logout, authenticate
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


@login_required
def user_profile(request):
    days_since_login = (timezone.now() - request.user.last_login).days

    # --- Subject Analysis Logic ---
    from django.db.models import Count, Case, When, IntegerField
    from django.core.paginator import Paginator
    from exam.models import UserQuestionResult, UserExamAttempt
    import json

    # 0. Recent Exam History (Pagination: 15 items)
    attempts_qs = UserExamAttempt.objects.filter(user=request.user).order_by(
        "-start_time"
    )
    paginator = Paginator(attempts_qs, 15)
    page_number = request.GET.get("page")
    recent_attempts = paginator.get_page(page_number)

    # 1. Aggregate results by Subject
    # We need to join Question -> Subject
    subject_stats = (
        UserQuestionResult.objects.filter(attempt__user=request.user)
        .values("question__subject__name")
        .annotate(
            total=Count("id"),
            correct=Count(
                Case(When(is_correct=True, then=1), output_field=IntegerField())
            ),
        )
    )

    # 2. Prepare data for Chart.js
    labels = []
    data = []
    weakest_subject = None
    min_accuracy = 101  # Start higher than 100

    for stat in subject_stats:
        subj_name = stat["question__subject__name"]
        accuracy = (
            round((stat["correct"] / stat["total"]) * 100, 1)
            if stat["total"] > 0
            else 0
        )

        labels.append(subj_name)
        data.append(accuracy)

        if accuracy < min_accuracy:
            min_accuracy = accuracy
            weakest_subject = f"{subj_name} ({accuracy}점)"

    # Handle case with no data
    if not labels:
        labels = ["데이터 없음"]
        data = [0]
        weakest_subject = "아직 학습 데이터가 충분하지 않습니다."

    context = {
        "days_since_login": days_since_login,
        "radar_labels": json.dumps(labels),
        "radar_data": json.dumps(data),
        "weakest_subject": weakest_subject,
        "recent_attempts": recent_attempts,
    }

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "accounts/profile_history_partial.html", context)

    return render(request, "accounts/profile.html", context)


@login_required
def profile_edit(request):
    if request.method == "POST":
        # Check if password verification step
        if "password_check" in request.POST:
            password = request.POST.get("password")
            if request.user.check_password(password):
                # Verify success -> Show edit form
                request.session["password_verified"] = True
                return redirect("accounts:profile_edit")
            else:
                messages.error(request, "비밀번호가 일치하지 않습니다.")

        # Check if actual profile update step
        elif "profile_update" in request.POST:
            if not request.session.get("password_verified"):
                return redirect("accounts:profile_edit")

            user = request.user
            user.email = request.POST.get("email")
            user.first_name = request.POST.get("first_name")
            user.save()

            messages.success(request, "회원정보가 수정되었습니다.")
            # Clear verification status
            del request.session["password_verified"]
            return redirect("accounts:user_profile")

    # GET Request
    if request.session.get("password_verified"):
        return render(request, "accounts/profile_edit.html", {"step": "edit"})
    else:
        return render(request, "accounts/profile_edit.html", {"step": "password"})
