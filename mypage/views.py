from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.db.models import Count, Case, When, IntegerField, Q
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
    # 0. Recent Exam History (Pagination: 15 items)
    attempts_qs = (
        UserExamAttempt.objects.filter(user=request.user)
        .annotate(
            total_q=Count("results"),
            correct_q=Count(
                Case(
                    When(results__is_correct=True, then=1),
                    output_field=IntegerField(),
                )
            ),
        )
        .order_by("-start_time")
    )
    attempts_paginator = Paginator(attempts_qs, 15)
    attempts_page = request.GET.get("page")
    recent_attempts = attempts_paginator.get_page(attempts_page)

    # 0.1 My Questions (Notebook History)
    # (Removed NotebookHistory from index context if not used, or kept if needed)

    # 0.2 My Questions (BBS Posts: Basic Book & Tree Doctor)
    target_types = ["기본서", "주치의", "주치의 질의"]
    posts_qs = Post.objects.filter(
        author=request.user, type__name__in=target_types
    ).order_by("-created_at")

    posts_paginator = Paginator(posts_qs, 15)
    posts_page = request.GET.get("q_page")
    my_questions = posts_paginator.get_page(posts_page)

    # 0.3 Wrong Answer Notes
    wrong_qs = (
        UserQuestionResult.objects.filter(attempt__user=request.user, is_correct=False)
        .select_related("question", "question__exam", "question__subject", "attempt")
        .order_by("-attempt__start_time", "question__number")
    )

    # Filter by Attempt ID if provided
    attempt_id = request.GET.get("attempt_id")
    mode = request.GET.get("mode")

    attempt = None
    if attempt_id:
        attempt = get_object_or_404(UserExamAttempt, id=attempt_id, user=request.user)
        wrong_qs = wrong_qs.filter(attempt=attempt)

        # Auto-generate Analysis if missing
        if mode == "full_details" and not attempt.ai_analysis:
            _generate_exam_analysis(attempt)

    if mode == "full_details":
        # No pagination for full details view
        wrong_answers = wrong_qs
    else:
        wrong_paginator = Paginator(wrong_qs, 15)
        wrong_page = request.GET.get("w_page")
        wrong_answers = wrong_paginator.get_page(wrong_page)

    # 1. Aggregate results by Subject
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
    min_accuracy = 101

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
        "wrong_answers": wrong_answers,
        "attempt_id": attempt_id,
        "attempt": attempt,
    }

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        # Check which part triggered AJAX
        if mode == "analysis_data":
            return JsonResponse(
                {"labels": labels, "data": data, "weakest_subject": weakest_subject}
            )
        if "q_page" in request.GET:
            return render(request, "mypage/my_questions_partial.html", context)
        if "w_page" in request.GET:
            return render(request, "mypage/wrong_answer_partial.html", context)
        if mode == "full_details":
            return render(request, "mypage/wrong_answer_full_list.html", context)
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


@login_required
def detail_answer(request, pk):
    post = get_object_or_404(Post, pk=pk)

    # Increment hits (consistent with bbs/views.py)
    post.hits += 1
    post.save()

    # Fetch 10 following (older) questions by the same author
    target_types = ["기본서", "주치의", "주치의 질의"]
    next_posts = Post.objects.filter(
        author=post.author, type__name__in=target_types, created_at__lt=post.created_at
    ).order_by("-created_at")[:10]

    context = {
        "post": post,
        "next_posts": next_posts,
    }
    context = {
        "post": post,
        "next_posts": next_posts,
    }
    return render(request, "mypage/detail_answer.html", context)


from django.views.decorators.http import require_POST
from django.conf import settings
import google.generativeai as genai
import markdown
from django.http import JsonResponse, HttpResponseBadRequest


from django.db.models import Count, Case, When, IntegerField, Q

# ... (rest of imports)


@login_required
def wrong_answer_detail(request, pk):
    result = get_object_or_404(UserQuestionResult, pk=pk, attempt__user=request.user)

    # Get next 10 wrong answers (ordered by time desc, id desc)
    # Next means: (time < current_time) OR (time == current_time AND id < current_id)
    next_results = (
        UserQuestionResult.objects.filter(attempt__user=request.user, is_correct=False)
        .filter(
            Q(attempt__start_time__lt=result.attempt.start_time)
            | Q(
                attempt__start_time=result.attempt.start_time,
                question__number__gt=result.question.number,
            )
        )
        .order_by("-attempt__start_time", "question__number")[:10]
    )

    return render(
        request,
        "mypage/wrong_answer_detail.html",
        {"result": result, "next_results": next_results},
    )


@login_required
@require_POST
def analyze_questions(request):
    try:
        # Fetch up to 20 recent questions (BBS Posts)
        target_types = ["기본서", "주치의", "주치의 질의"]
        recent_questions = Post.objects.filter(
            author=request.user, type__name__in=target_types
        ).order_by("-created_at")[:20]

        if not recent_questions:
            return JsonResponse(
                {"status": "error", "message": "분석할 질문 내역이 없습니다."}
            )

        # Construct Prompt
        questions_text = "\n".join(
            [f"- {q.title}: {q.content[:300]}..." for q in recent_questions]
        )
        prompt = (
            "당신은 '나무주치의' 합격반의 AI 멘토입니다. 학생이 그동안 질문한 내용을 바탕으로 학습 상태를 진단해주세요.\n"
            "다음은 학생의 최근 질문 목록입니다:\n"
            f"{questions_text}\n\n"
            "조건:\n"
            "1. 학생의 주요 관심 분야나 취약해 보이는 과목을 파악하세요.\n"
            "2. 학습 열정과 수준을 칭찬하고 격려하는 톤으로 작성하세요.\n"
            "3. 앞으로 더 학습해야 할 방향이나 팁을 구체적으로 제시하세요.\n"
            "4. Markdown 형식으로 깔끔하게 정리해서 답변해주세요."
        )

        # Call Gemini API
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-3-flash-preview")
        response = model.generate_content(prompt)

        # Convert Markdown to HTML
        analysis_html = markdown.markdown(response.text)

        return JsonResponse({"status": "success", "analysis": analysis_html})

    except Exception as e:
        print(f"Analysis Error: {e}")
        return JsonResponse(
            {"status": "error", "message": "분석 중 오류가 발생했습니다."}, status=500
        )


def _generate_exam_analysis(attempt):
    """
    Helper function to generate AI analysis for an exam attempt using Gemini.
    Returns the generated HTML content or None if generation failed/no wrong answers.
    """
    try:
        # Fetch Wrong Answers
        wrong_answers = (
            UserQuestionResult.objects.filter(attempt=attempt, is_correct=False)
            .select_related("question", "question__subject")
            .order_by("question__number")
        )

        if not wrong_answers.exists():
            return None

        # Construct Question Data for Prompt
        questions_text = ""
        for wa in wrong_answers:
            subject = wa.question.subject.name if wa.question.subject else "기타"
            content = wa.question.content[:200]
            # Use textbook_chat (Basic Book Explanation) if available, else general_chat or empty
            explanation = (
                getattr(wa.question, "textbook_chat", "")
                or getattr(wa.question, "general_chat", "")
                or "해설 없음"
            )

            questions_text += f"""
[{subject} - {wa.question.number}번]
문제: {content}
기본서 해설 요약: {explanation[:300]}
...
"""

        # Construct Analysis Prompt
        prompt = (
            f"당신은 '나무주치의' 자격증 시험 대비 AI 튜터입니다. 학생이 '{attempt.exam.round_number}회 모의고사'에서 틀린 문제들을 분석하여 맞춤형 리포트를 작성해주세요.\n\n"
            "다음은 학생이 틀린 문제와 관련 해설 내용입니다:\n"
            f"--- 시작 ---\n{questions_text}\n--- 끝 ---\n\n"
            "**요청 사항:**\n"
            "1. **취약 부분 진단**: 학생이 주로 어떤 과목이나 주제에서 약점을 보이는지 구체적으로 분석하세요.\n"
            "2. **보강해야 할 점**: 각 취약점을 보완하기 위해 어떤 키워드나 개념을 집중적으로 공부해야 하는지 '기본서 해설'을 바탕으로 제안하세요.\n"
            "3. **격려의 말**: 포기하지 않고 학습을 이어갈 수 있도록 동기를 부여하는 멘트로 마무리하세요.\n"
            "4. **형식**: Markdown을 사용하여 가독성 있게 작성해 주세요 (소제목, 글머리 기호 활용)."
        )

        # Call Gemini API
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        response = model.generate_content(prompt)

        # Convert Markdown to HTML
        analysis_html = markdown.markdown(response.text)

        # Save to DB
        attempt.ai_analysis = analysis_html
        attempt.save()

        return analysis_html

    except Exception as e:
        print(f"Gen AI Error: {e}")
        return None


@login_required
@require_POST
def analyze_attempt_wrong_answers(request, attempt_id):
    try:
        # Validate Attempt Ownership
        attempt = get_object_or_404(UserExamAttempt, id=attempt_id, user=request.user)

        if attempt.ai_analysis:
            return JsonResponse({"status": "success", "analysis": attempt.ai_analysis})

        analysis_html = _generate_exam_analysis(attempt)

        if analysis_html:
            return JsonResponse({"status": "success", "analysis": analysis_html})
        else:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "분석할 내용이 없거나 오류가 발생했습니다.",
                }
            )

    except Exception as e:
        print(f"Attempt Analysis Error: {e}")
        return JsonResponse(
            {"status": "error", "message": "시험 결과 분석 중 오류가 발생했습니다."},
            status=500,
        )


@login_required
@require_POST
def delete_attempt(request, attempt_id):
    try:
        attempt = get_object_or_404(UserExamAttempt, id=attempt_id, user=request.user)
        attempt.delete()
        return JsonResponse({"status": "success", "message": "삭제되었습니다."})
    except Exception as e:
        print(f"Error deleting attempt: {e}")
        return JsonResponse(
            {"status": "error", "message": "삭제 중 오류가 발생했습니다."}, status=500
        )
