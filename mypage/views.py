from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.db.models import Count, Case, When, IntegerField
from django.core.paginator import Paginator
import json

from exam.models import UserQuestionResult, UserExamAttempt
from notebook.models import NotebookHistory
from chat.models import ChatHistory
from bbs.models import Post


@login_required
def index(request):
    days_since_login = (timezone.now() - request.user.last_login).days

    # 0. Recent Exam History (Pagination: 15 items)
    attempts_qs = UserExamAttempt.objects.filter(user=request.user).order_by(
        "-start_time"
    )
    paginator = Paginator(attempts_qs, 15)
    page_number = request.GET.get("page")
    recent_attempts = paginator.get_page(page_number)

    # 0.1 My Questions (Notebook History)
    my_notebook_questions = NotebookHistory.objects.filter(user=request.user).order_by(
        "-created_at"
    )

    # 0.2 My Questions (BBS Posts: Basic Book & Tree Doctor)
    # Filter for posts where type is "기본서" or "주치의" (or "주치의 질의" for compatibility)
    target_types = ["기본서", "주치의", "주치의 질의"]
    my_questions = Post.objects.filter(
        author=request.user, type__name__in=target_types
    ).order_by("-created_at")

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
        "my_questions": my_questions,
    }

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "mypage/history_partial.html", context)

    return render(request, "mypage/index.html", context)


@login_required
def edit(request):
    if request.method == "POST":
        # Check if password verification step
        if "password_check" in request.POST:
            password = request.POST.get("password")
            if request.user.check_password(password):
                # Verify success -> Show edit form
                request.session["password_verified"] = True
                return redirect("mypage:edit")
            else:
                messages.error(request, "비밀번호가 일치하지 않습니다.")

        # Check if actual profile update step
        elif "profile_update" in request.POST:
            if not request.session.get("password_verified"):
                return redirect("mypage:edit")

            user = request.user
            user.email = request.POST.get("email")
            user.first_name = request.POST.get("first_name")

            # Password Change Logic
            current_password = request.POST.get("current_password")
            new_password = request.POST.get("new_password")
            new_password_confirm = request.POST.get("new_password_confirm")

            if new_password:
                if not user.check_password(current_password):
                    messages.error(
                        request,
                        "현재 비밀번호가 일치하지 않아 비밀번호를 변경할 수 없습니다.",
                    )
                elif new_password != new_password_confirm:
                    messages.error(request, "새 비밀번호가 일치하지 않습니다.")
                else:
                    user.set_password(new_password)
                    update_session_auth_hash(request, user)  # Important! Keep logged in

            user.save()

            # Clear verification status
            del request.session["password_verified"]
            return redirect("mypage:index")

    # GET Request
    if request.session.get("password_verified"):
        return render(request, "mypage/edit.html", {"step": "edit"})
    else:
        return render(request, "mypage/edit.html", {"step": "password"})
