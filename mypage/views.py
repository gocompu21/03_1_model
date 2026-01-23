from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.db import models
from django.db.models import Count, Case, When, IntegerField, Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from functools import wraps
import json

from exam.models import UserQuestionResult, UserExamAttempt
from notebook.models import NotebookHistory
from chat.models import ChatHistory
from bbs.models import Post
from .models import ReviewSchedule


def ajax_login_required(view_func):
    """
    Decorator for AJAX views that returns JSON error instead of redirecting to login page.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                "success": False, 
                "error": "로그인이 필요합니다.",
                "login_required": True
            }, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


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

    # --- Smart Review Recommendations ---
    today = timezone.localdate()  # Use local timezone (Asia/Seoul) instead of UTC
    review_recommendations = ReviewSchedule.objects.filter(
        user=request.user, next_review_date__lte=today, is_mastered=False
    ).select_related("question", "question__subject", "question__exam")[:10]
    review_count = ReviewSchedule.objects.filter(
        user=request.user, next_review_date__lte=today, is_mastered=False
    ).count()

    # --- Admin Dashboard Statistics ---
    admin_dashboard = None
    if request.user.is_staff or request.user.is_superuser:
        from django.contrib.auth.models import User
        from django.db.models import Avg, Max, FloatField
        from django.db.models.functions import Cast
        from exam.models import Subject
        from mock_exam.models import MockExam
        
        # User Statistics
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        recent_users = User.objects.filter(is_active=True).order_by('-date_joined')[:10]
        
        # Users with exam attempts
        users_with_attempts = UserExamAttempt.objects.values('user').distinct().count()
        
        # User performance data with basic stats
        from study.models import StudyViewLog
        user_qs = User.objects.annotate(
            exam_count=Count('exam_attempts'),
            avg_score=Avg('exam_attempts__total_score'),
            review_count=Count('review_schedules'),
            study_count=Count('study_view_logs'),
        ).filter(is_active=True).order_by('-exam_count')
        
        # Calculate last activity for each user
        user_stats = []
        for u in user_qs:
            # Get last activity times from different sources
            activities = []
            
            # Exam attempts
            last_exam = UserExamAttempt.objects.filter(user=u).order_by('-end_time').first()
            if last_exam and last_exam.end_time:
                activities.append(('기출시험', last_exam.end_time))
            
            # Mock exams
            last_mock = MockExam.objects.filter(user=u).order_by('-end_time').first()
            if last_mock and last_mock.end_time:
                activities.append(('모의고사', last_mock.end_time))
            
            # Chat history
            last_chat = ChatHistory.objects.filter(user=u).order_by('-created_at').first()
            if last_chat and last_chat.created_at:
                activities.append(('채팅', last_chat.created_at))
            
            # Notebook history
            last_notebook = NotebookHistory.objects.filter(user=u).order_by('-created_at').first()
            if last_notebook and last_notebook.created_at:
                activities.append(('노트북', last_notebook.created_at))
            
            # Study view log
            from study.models import StudyViewLog
            last_study = StudyViewLog.objects.filter(user=u).order_by('-viewed_at').first()
            if last_study and last_study.viewed_at:
                activities.append(('학습', last_study.viewed_at))
            
            # Review - use next_review_date as indicator of recent review activity
            last_review = ReviewSchedule.objects.filter(user=u, is_mastered=True).order_by('-next_review_date').first()
            if last_review and last_review.next_review_date:
                from datetime import datetime
                activities.append(('복습완료', timezone.make_aware(datetime.combine(last_review.next_review_date, datetime.min.time()))))
            
            # BBS Post
            last_post = Post.objects.filter(author=u).order_by('-created_at').first()
            if last_post and last_post.created_at:
                activities.append(('게시글', last_post.created_at))
            
            # Find most recent activity
            if activities:
                activities.sort(key=lambda x: x[1], reverse=True)
                last_activity_type, last_activity_time = activities[0]
            else:
                last_activity_type, last_activity_time = None, None
            
            # Get session duration data
            from accounts.models import UserSession
            today_duration = UserSession.get_user_today_duration(u)
            total_duration = UserSession.get_user_total_duration(u)
            
            # Get last logout time
            last_session = UserSession.objects.filter(user=u).order_by('-last_activity').first()
            last_logout_time = None
            if last_session:
                if last_session.logout_time:
                    last_logout_time = last_session.logout_time
                else:
                    last_logout_time = last_session.last_activity  # Still active or no logout
            
            user_stats.append({
                'username': u.username,
                'first_name': u.first_name,
                'last_login': u.last_login,
                'exam_count': u.exam_count,
                'avg_score': u.avg_score,
                'review_count': u.review_count,
                'study_count': u.study_count,
                'last_activity_type': last_activity_type,
                'last_activity_time': last_activity_time,
                'today_duration': UserSession.format_duration(today_duration),
                'total_duration': UserSession.format_duration(total_duration),
                'total_duration_raw': total_duration,  # For sorting
                'last_logout_time': last_logout_time,
            })
        
        # Sort user_stats by total duration (descending - most time first)
        user_stats.sort(key=lambda x: x.get('total_duration_raw', 0), reverse=True)
        
        # Subject statistics - overall correct rate by subject
        subject_stats = []
        for subject in Subject.objects.all().order_by('code'):
            results = UserQuestionResult.objects.filter(question__subject=subject)
            total = results.count()
            if total > 0:
                correct = results.filter(is_correct=True).count()
                avg_correct_rate = round((correct / total) * 100, 1)
                subject_stats.append({
                    'name': subject.name,
                    'avg_correct_rate': avg_correct_rate,
                    'total_attempts': total
                })
        
        # Sort by correct rate (ascending - worst first)
        subject_stats.sort(key=lambda x: x['avg_correct_rate'])
        
        admin_dashboard = {
            'total_users': total_users,
            'active_users': active_users,
            'users_with_attempts': users_with_attempts,
            'recent_users': recent_users,
            'user_stats': user_stats,
            'subject_stats': subject_stats
        }

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
        "review_recommendations": review_recommendations,
        "review_count": review_count,
        "admin_dashboard": admin_dashboard,
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
        
        # If this attempt was from a mock exam (round_number=0), also delete the MockExam
        if attempt.exam and attempt.exam.round_number == 0:
            from mock_exam.models import MockExam
            # Find MockExam by matching end_time (created at same time as UserExamAttempt)
            MockExam.objects.filter(
                user=request.user,
                end_time=attempt.end_time
            ).delete()
        
        attempt.delete()
        return JsonResponse({"status": "success", "message": "삭제되었습니다."})
    except Exception as e:
        print(f"Error deleting attempt: {e}")
        return JsonResponse(
            {"status": "error", "message": "삭제 중 오류가 발생했습니다."}, status=500
        )


from bbs.forms import PostForm


@login_required
def update_my_question(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author != request.user:
        return redirect("mypage:detail_answer", pk=post.pk)

    if request.method == "POST":
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            # Calculate page number
            target_types = ["기본서", "주치의", "주치의 질의"]
            newer_count = Post.objects.filter(
                author=request.user,
                type__name__in=target_types,
                created_at__gt=post.created_at,
            ).count()
            page_number = (newer_count // 15) + 1

            return redirect(
                reverse("mypage:index") + f"?tab=my_questions&q_page={page_number}"
            )
    else:
        form = PostForm(instance=post)

    return render(
        request,
        "bbs/post_form.html",
        {"form": form, "title": "나의 질문 수정", "btn_text": "수정"},
    )


@login_required
def delete_my_question(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author == request.user:
        # Calculate page number before deletion
        target_types = ["기본서", "주치의", "주치의 질의"]
        newer_count = Post.objects.filter(
            author=request.user,
            type__name__in=target_types,
            created_at__gt=post.created_at,
        ).count()
        page_number = (newer_count // 15) + 1

        post.delete()

        return redirect(
            reverse("mypage:index") + f"?tab=my_questions&q_page={page_number}"
        )
    return redirect(reverse("mypage:index") + "?tab=my_questions")


# --- Smart Review Session Views ---


@login_required
def review_start(request):
    """
    Start a review session with all questions due for review today.
    """
    today = timezone.localdate()  # Use local timezone (Asia/Seoul)
    review_items = ReviewSchedule.objects.filter(
        user=request.user, next_review_date__lte=today, is_mastered=False
    ).select_related("question", "question__subject", "question__exam")

    return render(
        request,
        "mypage/review_take.html",
        {
            "review_items": review_items,
            "total_count": review_items.count(),
        },
    )


@login_required
def review_submit(request):
    """
    Submit review answers and update review schedules.
    """
    if request.method == "POST":
        correct_count = 0
        total_count = 0
        results = []  # Collect detailed results

        # Get all schedule IDs from form
        for key, value in request.POST.items():
            if key.startswith("schedule_"):
                schedule_id = key.replace("schedule_", "")
                try:
                    schedule = ReviewSchedule.objects.select_related(
                        "question", "question__subject", "question__exam"
                    ).get(id=schedule_id, user=request.user)
                    selected_choice = int(value) if value else None

                    if selected_choice:
                        # Support list-based answers
                        is_correct = selected_choice in schedule.question.answer
                        schedule.mark_reviewed(is_correct)
                        total_count += 1
                        if is_correct:
                            correct_count += 1

                        # Add to results
                        results.append(
                            {
                                "schedule_id": schedule.id,
                                "question": schedule.question,
                                "selected_choice": selected_choice,
                                "is_correct": is_correct,
                                "review_count": schedule.review_count,
                            }
                        )
                except (ReviewSchedule.DoesNotExist, ValueError):
                    continue

        # Sort results by question number
        results.sort(key=lambda x: x["question"].number)

        # Return result
        return render(
            request,
            "mypage/review_result.html",
            {
                "results": results,
                "correct_count": correct_count,
                "total_count": total_count,
                "score": (
                    int((correct_count / total_count * 100)) if total_count > 0 else 0
                ),
            },
        )

    return redirect("mypage:index")


# --- Admin Prompt Generator ---

from django.contrib.admin.views.decorators import staff_member_required
from exam.models import Exam, Question
from django.http import JsonResponse
from django.conf import settings
import google.generativeai as genai


@staff_member_required
def prompt_generator(request):
    """
    Admin-only page to generate prompts for question explanations.
    Step 1: Generate prompt only
    Step 2: Query AI APIs via AJAX (separate endpoint)
    """
    exams = Exam.objects.exclude(round_number=0).order_by("round_number")

    generated_prompt = None
    selected_question = None

    if request.method == "POST":
        action = request.POST.get("action", "generate")
        round_number = request.POST.get("round_number")
        question_number = request.POST.get("question_number")

        # Handle DB update (AJAX)
        if action == "save_explanation":
            question_id = request.POST.get("question_id")
            explanation_text = request.POST.get("explanation_text")
            explanation_source = request.POST.get(
                "explanation_source"
            )  # 'basic_book' or 'tree_doctor'

            if question_id and explanation_text:
                try:
                    question = Question.objects.get(id=question_id)
                    # Save to appropriate field based on source
                    if explanation_source == "basic_book":
                        question.textbook_chat = explanation_text
                    else:  # tree_doctor
                        question.general_chat = explanation_text
                    question.save()
                    field_name = (
                        "기본서 해설"
                        if explanation_source == "basic_book"
                        else "일반 해설"
                    )
                    return JsonResponse(
                        {"success": True, "message": f"{field_name}이 저장되었습니다."}
                    )
                except Question.DoesNotExist:
                    return JsonResponse(
                        {"success": False, "message": "문제를 찾을 수 없습니다."}
                    )

        # Generate prompt only (Step 1)
        if round_number and question_number:
            try:
                question = Question.objects.get(
                    exam__round_number=round_number, number=question_number
                )
                selected_question = question

                answer_map = {1: "①", 2: "②", 3: "③", 4: "④", 5: "⑤"}
                # Handle list-based answers
                if isinstance(question.answer, list):
                    correct_answer = ", ".join([answer_map.get(a, str(a)) for a in question.answer])
                else:
                    correct_answer = answer_map.get(question.answer, str(question.answer))

                generated_prompt = f"""다음은 나무의사 시험 제{round_number}회 {question.subject.name} 문제입니다.

문제: {question.content}
①번. {question.choice1}
②번. {question.choice2}
③번. {question.choice3}
④번. {question.choice4}
⑤번. {question.choice5}

정답: {correct_answer}

위 문제에 대해 다음 형식으로 자세하고 전문적인 해설을 작성해주세요:

1. **정답 해설**: 왜 {correct_answer}이 정답인지 전체적으로 설명

2. **선지별 분석**:
   - ①번 {question.choice1}: (옳음/그름) 이유 설명
   - ②번 {question.choice2}: (옳음/그름) 이유 설명
   - ③번 {question.choice3}: (옳음/그름) 이유 설명
   - ④번 {question.choice4}: (옳음/그름) 이유 설명
   - ⑤번 {question.choice5}: (옳음/그름) 이유 설명

전문적이고 교육적인 해설을 작성해주세요."""

            except Question.DoesNotExist:
                generated_prompt = "해당 문제를 찾을 수 없습니다."

    return render(
        request,
        "mypage/prompt_generator.html",
        {
            "exams": exams,
            "generated_prompt": generated_prompt,
            "selected_question": selected_question,
        },
    )


@staff_member_required
def query_ai_api(request):
    """
    AJAX endpoint to query AI APIs (basic book or tree doctor).
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    api_type = request.POST.get("api_type")  # 'basic_book' or 'tree_doctor'
    prompt = request.POST.get("prompt")
    subject_name = request.POST.get("subject_name", "")

    if not prompt:
        return JsonResponse({"error": "No prompt provided"}, status=400)

    try:
        if api_type == "basic_book":
            from fileSearchStore import GeminiStoreManager

            manager = GeminiStoreManager(api_key=settings.GEMINI_API_KEY)
            response_text = manager.query_store(subject_name, prompt)
        else:  # tree_doctor
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-3-flash-preview")
            response = model.generate_content(prompt)
            response_text = response.text

        return JsonResponse({"success": True, "response": response_text})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


NARRATION_PROMPT = """당신은 나무의사 자격 시험을 준비하는 수험생을 위한 전문 강사입니다.

다음 문제와 해설을 바탕으로, 음성으로 들려줄 전문적이고 명확한 나레이션을 작성해주세요.

[요구사항]
1. 맨 앞에 인사나 다른 말을 하지 말고, 문제를 읽지 말고 바로 정답 해설로 시작하세요.
2. 마지막에 "수험생 여러분" 등의 감사 인사를 하지 말고 깔끔하게 설명으로 끝내세요.
3. 전문 용어는 쉽게 풀어서 설명해주세요.
4. 중요한 포인트는 **굵게** 표시하여 강조해주세요.
5. 자연스럽게 읽을 수 있는 문장으로 작성해주세요.
6. LaTeX 수식이나 특수 기호는 읽을 수 있는 텍스트로 변환해주세요.
7. 마크다운 형식(**, *, - 등)을 활용하여 가독성을 높여주세요.

[문제]
{question_content}

[보기]
① {choice1}
② {choice2}
③ {choice3}
④ {choice4}
⑤ {choice5}

[정답]
{answer}번

[기본서 해설]
{textbook_chat}

위 내용을 바탕으로 전문적이고 명확한 나레이션을 마크다운 형식으로 작성해주세요."""


@staff_member_required
def generate_narration_api(request):
    """
    AJAX endpoint to generate narration for a question.
    Requires question_id in POST data.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    question_id = request.POST.get("question_id")
    if not question_id:
        return JsonResponse({"error": "No question_id provided"}, status=400)

    try:
        question = Question.objects.get(id=question_id)
        
        # Check if textbook_chat exists
        if not question.textbook_chat:
            return JsonResponse({
                "success": False, 
                "error": "기본서 해설이 없습니다. 먼저 기본서에 질문하여 해설을 생성하세요."
            })
        
        # Build narration prompt
        prompt = NARRATION_PROMPT.format(
            question_content=question.content,
            choice1=question.choice1,
            choice2=question.choice2,
            choice3=question.choice3,
            choice4=question.choice4,
            choice5=question.choice5,
            answer=question.answer[0] if isinstance(question.answer, list) else question.answer,
            textbook_chat=question.textbook_chat
        )
        
        # Call Gemini API
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-3-flash-preview")
        response = model.generate_content(prompt)
        narration_text = response.text
        
        return JsonResponse({"success": True, "response": narration_text})

    except Question.DoesNotExist:
        return JsonResponse({"success": False, "error": "문제를 찾을 수 없습니다."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@staff_member_required
def save_narration_api(request):
    """
    AJAX endpoint to save narration to database.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    question_id = request.POST.get("question_id")
    narration_text = request.POST.get("narration_text")
    
    if not question_id or not narration_text:
        return JsonResponse({"error": "Missing question_id or narration_text"}, status=400)

    try:
        question = Question.objects.get(id=question_id)
        question.narration = narration_text
        question.save()
        return JsonResponse({"success": True, "message": "나레이션이 저장되었습니다."})
    except Question.DoesNotExist:
        return JsonResponse({"success": False, "error": "문제를 찾을 수 없습니다."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@staff_member_required
def generate_tts_api(request):
    """
    AJAX endpoint to generate TTS audio from narration text.
    Uses shared TTS generator utility module.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    question_id = request.POST.get("question_id")
    narration_text = request.POST.get("narration_text")
    
    if not question_id or not narration_text:
        return JsonResponse({"error": "Missing question_id or narration_text"}, status=400)

    try:
        question = Question.objects.get(id=question_id)
        round_num = question.exam.round_number
        q_num = question.number
        
        # Use shared TTS generator
        from utils.tts_generator import generate_tts_audio
        import os
        import uuid
        
        # Generate filename and path
        tts_dir = os.path.join(settings.MEDIA_ROOT, "tts")
        unique_id = uuid.uuid4().hex[:6]
        filename = f"round{round_num}_q{q_num}_narration_{unique_id}.mp3"
        filepath = os.path.join(tts_dir, filename)
        
        # Generate TTS using shared module
        result = generate_tts_audio(narration_text, filepath)
        
        if result["success"]:
            file_url = f"{settings.MEDIA_URL}tts/{filename}"
            return JsonResponse({
                "success": True, 
                "message": f"TTS 생성 완료: {filename}",
                "file_url": file_url,
                "filename": filename
            })
        else:
            return JsonResponse({"success": False, "error": result["message"]})
        
    except Question.DoesNotExist:
        return JsonResponse({"success": False, "error": "문제를 찾을 수 없습니다."})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"success": False, "error": str(e)})


@staff_member_required
def get_existing_tts_api(request):
    """
    AJAX endpoint to get existing TTS audio file for a question.
    Returns the URL of the most recent TTS file if it exists.
    """
    question_id = request.GET.get("question_id")
    if not question_id:
        return JsonResponse({"success": False, "error": "Missing question_id"})

    try:
        import os
        import glob
        
        question = Question.objects.get(id=question_id)
        round_num = question.exam.round_number
        q_num = question.number
        
        # Search for existing TTS files
        tts_dir = os.path.join(settings.MEDIA_ROOT, "tts")
        pattern = os.path.join(tts_dir, f"round{round_num}_q{q_num}_*narration*.mp3")
        files = glob.glob(pattern)
        
        if files:
            # Get the most recent file
            latest_file = max(files, key=os.path.getmtime)
            filename = os.path.basename(latest_file)
            file_url = f"{settings.MEDIA_URL}tts/{filename}"
            return JsonResponse({
                "success": True,
                "exists": True,
                "file_url": file_url,
                "filename": filename
            })
        else:
            return JsonResponse({
                "success": True,
                "exists": False,
                "message": "TTS 파일이 없습니다. 먼저 TTS 음성을 생성하세요."
            })
        
    except Question.DoesNotExist:
        return JsonResponse({"success": False, "error": "문제를 찾을 수 없습니다."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@staff_member_required
def generate_infographic_api(request):
    """
    AJAX endpoint to generate infographic image using Gemini API.
    Uses gemini-3-pro-image-preview model for image generation.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    question_id = request.POST.get("question_id")
    prompt = request.POST.get("prompt")
    
    if not question_id or not prompt:
        return JsonResponse({"error": "Missing question_id or prompt"}, status=400)

    try:
        import os
        import mimetypes
        from google import genai
        from google.genai import types
        from django.core.files.base import ContentFile
        
        question = Question.objects.get(id=question_id)
        round_num = question.exam.round_number
        q_num = question.number
        
        # Configure Gemini client
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        model = "gemini-3-pro-image-preview"
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                ],
            ),
        ]
        generate_content_config = types.GenerateContentConfig(
            response_modalities=[
                "IMAGE",
                "TEXT",
            ],
            image_config=types.ImageConfig(
                image_size="1K",
            ),
        )
        
        # Generate image
        image_data = None
        mime_type = None
        
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if (
                chunk.candidates is None
                or chunk.candidates[0].content is None
                or chunk.candidates[0].content.parts is None
            ):
                continue
            
            part = chunk.candidates[0].content.parts[0]
            if part.inline_data and part.inline_data.data:
                image_data = part.inline_data.data
                mime_type = part.inline_data.mime_type
                break  # Got the image, stop
        
        if not image_data:
            return JsonResponse({
                "success": False, 
                "error": "이미지 생성에 실패했습니다. 다시 시도해주세요."
            })
        
        # Determine file extension
        file_extension = mimetypes.guess_extension(mime_type) or ".png"
        
        # Add timestamp to filename to prevent browser caching issues
        import time
        timestamp = int(time.time())
        filename = f"infographic_{round_num}_{q_num}_{timestamp}{file_extension}"
        
        # Save to temporary folder instead of database
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_infographics')
        os.makedirs(temp_dir, exist_ok=True)
        temp_filepath = os.path.join(temp_dir, filename)
        
        with open(temp_filepath, 'wb') as f:
            f.write(image_data)
        
        # Generate URL for temporary file
        temp_url = os.path.join(settings.MEDIA_URL, 'temp_infographics', filename).replace('\\', '/')
        
        return JsonResponse({
            "success": True,
            "message": f"인포그래픽 이미지 생성 완료: {filename}",
            "image_url": temp_url,
            "temp_filename": filename,
            "is_temp": True
        })
        
    except Question.DoesNotExist:
        return JsonResponse({"success": False, "error": "문제를 찾을 수 없습니다."})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"success": False, "error": str(e)})


@staff_member_required
def save_infographic_api(request):
    """
    AJAX endpoint to save temporary infographic image to Question.infographic_image field.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    question_id = request.POST.get("question_id")
    temp_filename = request.POST.get("temp_filename")
    
    if not question_id or not temp_filename:
        return JsonResponse({"error": "Missing question_id or temp_filename"}, status=400)

    try:
        import os
        from django.core.files import File
        
        question = Question.objects.get(id=question_id)
        
        # Get temporary file path
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_infographics')
        temp_filepath = os.path.join(temp_dir, temp_filename)
        
        if not os.path.exists(temp_filepath):
            return JsonResponse({
                "success": False, 
                "error": "임시 파일을 찾을 수 없습니다."
            })
        
        # Delete existing infographic image if exists
        if question.infographic_image:
            question.infographic_image.delete(save=False)
        
        # Save temp file to Question.infographic_image field
        with open(temp_filepath, 'rb') as f:
            question.infographic_image.save(
                temp_filename,
                File(f),
                save=True
            )
        
        # Delete temporary file
        try:
            os.remove(temp_filepath)
        except:
            pass  # Ignore errors when deleting temp file
        
        return JsonResponse({
            "success": True,
            "message": "인포그래픽 이미지가 저장되었습니다.",
            "image_url": question.infographic_image.url
        })
        
    except Question.DoesNotExist:
        return JsonResponse({"success": False, "error": "문제를 찾을 수 없습니다."})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"success": False, "error": str(e)})


# --- Practice Question Input Views (CSV Upload) ---
from practice.models import Book, Chapter, PracticeQuestion
import csv
from io import StringIO


@ajax_login_required
def practice_input_get_books(request):
    """AJAX endpoint to get list of books with their chapters."""
    if not request.user.is_superuser:
        return JsonResponse({"success": False, "error": "권한이 없습니다."}, status=403)
    
    books = Book.objects.all().prefetch_related('chapters')
    books_data = []
    
    def natural_sort_key(chapter):
        """Sort chapters naturally by code (1.1 < 1.2 < 1.10 < 2.1)"""
        # Handle None or empty strings
        if not chapter.code:
            return []
            
        parts = chapter.code.split('.')
        # Use tuple comparison (type_priority, value) to safely compare int vs str
        # 0 for int, 1 for str -> Numbers come first
        return [
            (0, int(p)) if p.isdigit() else (1, p) 
            for p in parts
        ]
    
    for book in books:
        chapters = list(book.chapters.all())
        chapters.sort(key=natural_sort_key)
        chapters_data = [
            {
                "id": c.id,
                "code": c.code,
                "title": c.title,
                "level": c.level,
                "full_path": c.get_full_path()
            }
            for c in chapters
        ]
        books_data.append({
            "id": book.id,
            "name": book.name,
            "subject": book.subject,
            "chapters": chapters_data
        })
    
    return JsonResponse({"success": True, "books": books_data})


@ajax_login_required
@require_POST
def practice_input_parse_csv(request):
    """Parse CSV text and return structured question data."""
    if not request.user.is_superuser:
        return JsonResponse({"success": False, "error": "권한이 없습니다."}, status=403)
    
    csv_text = request.POST.get("csv_text", "")
    
    if not csv_text.strip():
        return JsonResponse({"success": False, "error": "CSV 내용이 비어있습니다."})
    
    try:
        questions = []
        reader = csv.reader(StringIO(csv_text), delimiter='\t')
        
        for row_idx, row in enumerate(reader, start=1):
            # Skip empty rows
            if not row or not any(row):
                continue
            
            # Skip header row if detected
            if row_idx == 1 and row[0].strip().lower() in ['번호', '문제번호', 'number', '#', '문제', '문제내용', 'content', 'question']:
                continue
            
            # Ensure minimum columns (number + content + 5 choices + answer = 8)
            if len(row) < 8:
                questions.append({
                    "row": row_idx,
                    "error": f"열이 부족합니다 (최소 8개 필요, {len(row)}개 제공)",
                    "content": row[1] if len(row) > 1 else row[0] if row else ""
                })
                continue
            
            try:
                number = int(row[0].strip()) if row[0] and row[0].strip() else 0
            except ValueError:
                number = 0
            
            content = row[1].strip() if len(row) > 1 and row[1] else ""
            choice1 = row[2].strip() if len(row) > 2 and row[2] else ""
            choice2 = row[3].strip() if len(row) > 3 and row[3] else ""
            choice3 = row[4].strip() if len(row) > 4 and row[4] else ""
            choice4 = row[5].strip() if len(row) > 5 and row[5] else ""
            choice5 = row[6].strip() if len(row) > 6 and row[6] else ""
            
            try:
                answer = int(row[7].strip()) if len(row) > 7 and row[7].strip() else 0
            except ValueError:
                answer = 0
            
            explanation = row[8].strip() if len(row) > 8 and row[8] else ""
            
            questions.append({
                "row": row_idx,
                "number": number,
                "content": content,
                "choice1": choice1,
                "choice2": choice2,
                "choice3": choice3,
                "choice4": choice4,
                "choice5": choice5,
                "answer": answer,
                "explanation": explanation,
                "error": None
            })
        
        if not questions:
            return JsonResponse({"success": False, "error": "파싱된 문제가 없습니다."})
        
        return JsonResponse({"success": True, "questions": questions})
    
    except Exception as e:
        return JsonResponse({"success": False, "error": f"CSV 파싱 오류: {str(e)}"})


@ajax_login_required
@require_POST
def practice_input_save(request):
    """Save parsed questions to database."""
    if not request.user.is_superuser:
        return JsonResponse({"success": False, "error": "권한이 없습니다."}, status=403)
    
    try:
        data = json.loads(request.body)
        chapter_id = data.get("chapter_id")
        questions = data.get("questions", [])
        
        # Debug logging
        print(f"[DEBUG] practice_input_save called")
        print(f"[DEBUG] chapter_id: {chapter_id}, type: {type(chapter_id)}")
        print(f"[DEBUG] questions count: {len(questions)}")
        if questions:
            print(f"[DEBUG] first question: {questions[0]}")
        
        if not chapter_id:
            return JsonResponse({"success": False, "error": "목차를 선택해주세요."})
        
        if not questions:
            return JsonResponse({"success": False, "error": "저장할 문제가 없습니다."})
        
        chapter = get_object_or_404(Chapter, id=chapter_id)
        
        # Get current max question number for this chapter
        last_q = PracticeQuestion.objects.filter(chapter=chapter).order_by('-number').first()
        next_number = (last_q.number + 1) if last_q else 1
        
        created_count = 0
        errors = []
        
        for q in questions:
            if q.get("error"):
                continue
            
            content = q.get("content", "").strip()
            if not content:
                errors.append(f"문제 {q.get('row', '?')}: 문제 내용이 비어있습니다.")
                continue
            
            answer = q.get("answer", 0)
            try:
                answer = int(answer) if answer else 0
            except (ValueError, TypeError):
                errors.append(f"문제 {q.get('row', '?')}: 정답이 올바르지 않습니다.")
                continue
            
            if not (1 <= answer <= 5):
                errors.append(f"문제 {q.get('row', '?')}: 정답은 1-5 사이여야 합니다.")
                continue
            
            # Use number from CSV if provided and valid, otherwise auto-increment
            q_number = q.get("number", 0)
            if q_number and q_number > 0:
                # Check if this number already exists for the chapter
                if PracticeQuestion.objects.filter(chapter=chapter, number=q_number).exists():
                    # Auto-assign next available number instead of erroring
                    use_number = next_number
                    next_number += 1
                else:
                    use_number = q_number
            else:
                use_number = next_number
                next_number += 1
            
            PracticeQuestion.objects.create(
                chapter=chapter,
                number=use_number,
                content=content,
                choice1=q.get("choice1", ""),
                choice2=q.get("choice2", ""),
                choice3=q.get("choice3", ""),
                choice4=q.get("choice4", ""),
                choice5=q.get("choice5", ""),
                answer=answer,
                explanation=q.get("explanation", ""),
            )
            created_count += 1
        
        if errors:
            return JsonResponse({
                "success": True,
                "message": f"{created_count}개 문제 추가됨. 오류: {'; '.join(errors[:5])}",
                "created_count": created_count,
                "errors": errors
            })
        
        return JsonResponse({
            "success": True,
            "message": f"{created_count}개 문제가 성공적으로 추가되었습니다.",
            "created_count": created_count
        })
    
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "잘못된 요청 형식입니다."})
    except Exception as e:
        return JsonResponse({"success": False, "error": f"저장 중 오류: {str(e)}"})


from difflib import SequenceMatcher

def similarity_ratio(a: str, b: str) -> float:
    """Returns a similarity ratio between 0.0 and 1.0"""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


@ajax_login_required
@require_POST
def practice_input_check_similarity(request):
    """Check similarity of parsed questions against existing questions in the chapter."""
    if not request.user.is_superuser:
        return JsonResponse({"success": False, "error": "권한이 없습니다."}, status=403)
    
    try:
        data = json.loads(request.body)
        chapter_id = data.get("chapter_id")
        questions = data.get("questions", [])
        
        if not chapter_id:
            return JsonResponse({"success": False, "error": "챕터를 선택해주세요."})
        
        # Get existing questions in the chapter
        existing_questions = PracticeQuestion.objects.filter(chapter_id=chapter_id)
        
        similarities = []
        
        for q in questions:
            content = q.get("content", "").strip()
            choices = [
                q.get("choice1", "").strip(),
                q.get("choice2", "").strip(),
                q.get("choice3", "").strip(),
                q.get("choice4", "").strip(),
                q.get("choice5", "").strip(),
            ]
            
            max_content_sim = 0.0
            max_choices_sim = 0.0
            
            for existing in existing_questions:
                # Calculate content similarity
                content_sim = similarity_ratio(content, existing.content)
                
                if content_sim > max_content_sim:
                    max_content_sim = content_sim
                    # Calculate choices similarity for the most similar content
                    existing_choices = [
                        existing.choice1, existing.choice2, existing.choice3,
                        existing.choice4, existing.choice5
                    ]
                    choice_sims = [
                        similarity_ratio(c, ec) for c, ec in zip(choices, existing_choices)
                    ]
                    max_choices_sim = sum(choice_sims) / 5 if choice_sims else 0.0
            
            similarities.append({
                "content_sim": round(max_content_sim * 100, 1),
                "choices_sim": round(max_choices_sim * 100, 1)
            })
        
        return JsonResponse({"success": True, "similarities": similarities})
    
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "잘못된 요청 형식입니다."})
    except Exception as e:
        return JsonResponse({"success": False, "error": f"유사도 검사 오류: {str(e)}"})


@ajax_login_required
@require_POST
def practice_input_get_textbook_explanation(request):
    """Get explanation from textbook using GeminiStoreManager."""
    if not request.user.is_superuser:
        return JsonResponse({"success": False, "error": "권한이 없습니다."}, status=403)
    
    try:
        # Import dynamically to avoid top-level failures and handle path issues
        try:
            from fileSearchStore import GeminiStoreManager, SYSTEM_INSTRUCTION as TEXTBOOK_INSTRUCTION
        except ImportError:
            # Fallback: try adding project root to path
            import sys
            import os
            from django.conf import settings
            if str(settings.BASE_DIR) not in sys.path:
                sys.path.append(str(settings.BASE_DIR))
            from fileSearchStore import GeminiStoreManager, SYSTEM_INSTRUCTION as TEXTBOOK_INSTRUCTION
    except Exception as e:
         return JsonResponse({"success": False, "error": f"모듈 로드 오류: {str(e)}"})
    
    try:
        data = json.loads(request.body)
        content = data.get("content", "").strip()
        choices = [
            data.get("choice1", ""),
            data.get("choice2", ""),
            data.get("choice3", ""),
            data.get("choice4", ""),
            data.get("choice5", ""),
        ]
        
        if not content:
            return JsonResponse({"success": False, "error": "문제 내용이 없습니다."})
        
        # Get API key from settings
        from django.conf import settings
        api_key = getattr(settings, "GEMINI_API_KEY", "")
        
        if not api_key:
            return JsonResponse({"success": False, "error": "API 키가 설정되지 않았습니다."})
        
        # Initialize manager
        manager = GeminiStoreManager(api_key=api_key)
        
        # Build prompt similar to app_getTextbook.py
        prompt_content = (
            f"{content}\n"
            f"① {choices[0]}\n"
            f"② {choices[1]}\n"
            f"③ {choices[2]}\n"
            f"④ {choices[3]}\n"
            f"⑤ {choices[4]}"
        )
        
        prompt = f"{TEXTBOOK_INSTRUCTION}\n\n[문제]\n{prompt_content}"
        
        # Query the store (default to 수목관리학 or try to infer)
        # For now, use 수목관리학 as default store
        store_name = "수목관리학"
        response_text = manager.query_store(store_name, prompt)
        
        if "Error" in response_text or "not found" in response_text.lower():
            # Try other stores
            for fallback in ["수목병리학", "수목생리학", "수목해충학", "산림토양학"]:
                response_text = manager.query_store(fallback, prompt)
                if "Error" not in response_text and "not found" not in response_text.lower():
                    break
        
        return JsonResponse({"success": True, "explanation": response_text})
    
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "잘못된 요청 형식입니다."})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"success": False, "error": f"기본서 조회 오류: {str(e)}"})


# --- Practice Question Management (Edit/Delete) ---

@ajax_login_required
def practice_input_get_questions(request):
    """Get existing questions for a chapter."""
    if not request.user.is_superuser:
        return JsonResponse({"success": False, "error": "권한이 없습니다."}, status=403)
    
    chapter_id = request.GET.get("chapter_id")
    if not chapter_id:
        return JsonResponse({"success": False, "error": "목차를 선택해주세요."})
    
    try:
        questions = PracticeQuestion.objects.filter(chapter_id=chapter_id).order_by('number')
        questions_data = [
            {
                "id": q.id,
                "number": q.number,
                "content": q.content,
                "choice1": q.choice1,
                "choice2": q.choice2,
                "choice3": q.choice3,
                "choice4": q.choice4,
                "choice5": q.choice5,
                "answer": q.answer,
                "explanation": q.explanation or "",
            }
            for q in questions
        ]
        return JsonResponse({"success": True, "questions": questions_data})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@ajax_login_required
@require_POST
def practice_input_update_question(request):
    """Update a single practice question."""
    if not request.user.is_superuser:
        return JsonResponse({"success": False, "error": "권한이 없습니다."}, status=403)
    
    try:
        data = json.loads(request.body)
        question_id = data.get("id")
        
        if not question_id:
            return JsonResponse({"success": False, "error": "문제 ID가 필요합니다."})
        
        question = get_object_or_404(PracticeQuestion, id=question_id)
        
        # Update fields
        question.number = data.get("number", question.number)
        question.content = data.get("content", question.content)
        question.choice1 = data.get("choice1", question.choice1)
        question.choice2 = data.get("choice2", question.choice2)
        question.choice3 = data.get("choice3", question.choice3)
        question.choice4 = data.get("choice4", question.choice4)
        question.choice5 = data.get("choice5", question.choice5)
        question.answer = data.get("answer", question.answer)
        question.explanation = data.get("explanation", question.explanation)
        question.save()
        
        return JsonResponse({"success": True, "message": "문제가 수정되었습니다."})
    
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "잘못된 요청 형식입니다."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@ajax_login_required
@require_POST
def practice_input_delete_question(request):
    """Delete a single practice question and renumber remaining questions."""
    if not request.user.is_superuser:
        return JsonResponse({"success": False, "error": "권한이 없습니다."}, status=403)
    
    try:
        data = json.loads(request.body)
        question_id = data.get("id")
        
        if not question_id:
            return JsonResponse({"success": False, "error": "문제 ID가 필요합니다."})
        
        question = get_object_or_404(PracticeQuestion, id=question_id)
        chapter = question.chapter
        question.delete()
        
        # Renumber remaining questions in the same chapter
        remaining_questions = PracticeQuestion.objects.filter(chapter=chapter).order_by('number')
        for idx, q in enumerate(remaining_questions, start=1):
            if q.number != idx:
                q.number = idx
                q.save(update_fields=['number'])
        
        return JsonResponse({"success": True, "message": "문제가 삭제되고 번호가 재정렬되었습니다."})
    
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "잘못된 요청 형식입니다."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


# --- Chapter Tree Management Views ---

@login_required
def chapter_list_api(request):
    """Return chapter tree data for a given book as JSON."""
    if not request.user.is_superuser:
        return JsonResponse({"success": False, "error": "권한이 없습니다."}, status=403)
    
    book_id = request.GET.get("book_id")
    if not book_id:
        return JsonResponse({"success": False, "error": "교재를 선택해주세요."})
    
    try:
        chapters = Chapter.objects.filter(book_id=book_id).order_by('order', 'code')
        
        def build_tree(parent_id=None):
            """Recursively build chapter tree."""
            result = []
            for ch in chapters:
                if ch.parent_id == parent_id:
                    children = build_tree(ch.id)
                    result.append({
                        "id": ch.id,
                        "code": ch.code,
                        "title": ch.title,
                        "level": ch.level,
                        "order": ch.order,
                        "parent_id": ch.parent_id,
                        "has_children": len(children) > 0,
                        "children": children
                    })
            return result
        
        tree = build_tree(None)
        return JsonResponse({"success": True, "chapters": tree})
    
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


def reorder_chapter_codes(book_id, parent_id):
    """
    Recursively update codes of siblings and their descendants based on 'order'.
    """
    siblings = Chapter.objects.filter(book_id=book_id, parent_id=parent_id).order_by('order')
    
    parent_code = ""
    if parent_id:
        try:
            parent = Chapter.objects.get(id=parent_id)
            parent_code = parent.code
        except Chapter.DoesNotExist:
            return

    for idx, chapter in enumerate(siblings, 1):
        new_code = f"{parent_code}.{idx}" if parent_code else str(idx)
        
        if chapter.code != new_code:
            chapter.code = new_code
            chapter.save(update_fields=['code'])
            reorder_chapter_codes(book_id, chapter.id)

@login_required
@require_POST
def chapter_create(request):
    """Create a new chapter (sibling or child)."""
    if not request.user.is_superuser:
        return JsonResponse({"success": False, "error": "권한이 없습니다."}, status=403)
    
    try:
        data = json.loads(request.body)
        book_id = data.get("book_id")
        parent_id = data.get("parent_id")  # None for root level
        reference_id = data.get("reference_id")  # Chapter to add sibling/child to
        add_type = data.get("add_type", "sibling")  # "sibling" or "child"
        code = data.get("code", "").strip()
        title = data.get("title", "").strip()
        
        if not book_id:
            return JsonResponse({"success": False, "error": "교재를 선택해주세요."})
        if not code or not title:
            return JsonResponse({"success": False, "error": "코드와 제목을 입력해주세요."})
        
        book = get_object_or_404(Book, id=book_id)
        
        if add_type == "child" and reference_id:
            # Add as child of reference chapter
            parent_chapter = get_object_or_404(Chapter, id=reference_id)
            parent_id = parent_chapter.id
            level = parent_chapter.level + 1
            # Get max order among siblings
            siblings = Chapter.objects.filter(book=book, parent_id=parent_id)
            max_order = siblings.aggregate(models.Max('order'))['order__max'] or 0
            new_order = max_order + 1
        else:
            # Add as sibling
            if reference_id:
                ref_chapter = get_object_or_404(Chapter, id=reference_id)
                parent_id = ref_chapter.parent_id
                level = ref_chapter.level
                # Insert after reference chapter
                new_order = ref_chapter.order + 1
                # Shift orders of following siblings
                Chapter.objects.filter(
                    book=book, 
                    parent_id=parent_id, 
                    order__gte=new_order
                ).update(order=models.F('order') + 1)
            else:
                # Add at root level
                parent_id = None
                level = 1
                max_order = Chapter.objects.filter(book=book, parent_id=None).aggregate(models.Max('order'))['order__max'] or 0
                new_order = max_order + 1
        
        new_chapter = Chapter.objects.create(
            book=book,
            parent_id=parent_id,
            code=code,
            title=title,
            level=level,
            order=new_order
        )
        
        # Reorder codes to ensure consistency
        reorder_chapter_codes(book.id, parent_id)
        new_chapter.refresh_from_db()
        
        return JsonResponse({
            "success": True, 
            "message": "목차가 추가되었습니다.",
            "chapter": {
                "id": new_chapter.id,
                "code": new_chapter.code,
                "title": new_chapter.title,
                "level": new_chapter.level,
                "order": new_chapter.order
            }
        })
    
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "잘못된 요청 형식입니다."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@require_POST
def chapter_update(request, chapter_id):
    """Update chapter code and title."""
    if not request.user.is_superuser:
        return JsonResponse({"success": False, "error": "권한이 없습니다."}, status=403)
    
    try:
        data = json.loads(request.body)
        code = data.get("code", "").strip()
        title = data.get("title", "").strip()
        
        if not code or not title:
            return JsonResponse({"success": False, "error": "코드와 제목을 입력해주세요."})
        
        chapter = get_object_or_404(Chapter, id=chapter_id)
        chapter.code = code
        chapter.title = title
        chapter.save()
        
        return JsonResponse({"success": True, "message": "목차가 수정되었습니다."})
    
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "잘못된 요청 형식입니다."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@require_POST
def chapter_delete(request, chapter_id):
    """Delete a chapter (only if no children)."""
    if not request.user.is_superuser:
        return JsonResponse({"success": False, "error": "권한이 없습니다."}, status=403)
    
    try:
        chapter = get_object_or_404(Chapter, id=chapter_id)
        
        # Check for children
        if Chapter.objects.filter(parent_id=chapter_id).exists():
            return JsonResponse({
                "success": False, 
                "error": "자식 목차가 있어 삭제할 수 없습니다. 먼저 자식 목차를 삭제해주세요."
            })
        
        # Check for questions
        if chapter.questions.exists():
            return JsonResponse({
                "success": False,
                "error": f"이 목차에 {chapter.questions.count()}개의 문제가 있어 삭제할 수 없습니다."
            })
        
        parent_id = chapter.parent_id
        book_id = chapter.book_id
        chapter.delete()
        
        # Reorder remaining siblings
        reorder_chapter_codes(book_id, parent_id)
        
        return JsonResponse({"success": True, "message": "목차가 삭제되었습니다."})
    
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@require_POST
def chapter_move(request, chapter_id):
    """Move chapter up or down among siblings."""
    if not request.user.is_superuser:
        return JsonResponse({"success": False, "error": "권한이 없습니다."}, status=403)
    
    try:
        data = json.loads(request.body)
        direction = data.get("direction", "up")  # "up" or "down"
        
        chapter = get_object_or_404(Chapter, id=chapter_id)
        siblings = Chapter.objects.filter(
            book=chapter.book, 
            parent_id=chapter.parent_id
        ).order_by('order')
        
        siblings_list = list(siblings)
        current_index = next((i for i, ch in enumerate(siblings_list) if ch.id == chapter.id), None)
        
        if current_index is None:
            return JsonResponse({"success": False, "error": "목차를 찾을 수 없습니다."})
        
        if direction == "up" and current_index > 0:
            # Swap with previous sibling
            swap_target = siblings_list[current_index - 1]
            chapter.order, swap_target.order = swap_target.order, chapter.order
            chapter.save()
            swap_target.save()
        elif direction == "down" and current_index < len(siblings_list) - 1:
            # Swap with next sibling
            swap_target = siblings_list[current_index + 1]
            chapter.order, swap_target.order = swap_target.order, chapter.order
            chapter.save()
            swap_target.save()
        else:
            return JsonResponse({"success": False, "error": "더 이상 이동할 수 없습니다."})
        
        # Reorder codes
        reorder_chapter_codes(chapter.book_id, chapter.parent_id)
        
        return JsonResponse({"success": True, "message": "순서가 변경되었습니다."})
    
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "잘못된 요청 형식입니다."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})
