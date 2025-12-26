from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
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
from .models import ReviewSchedule


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
        user_qs = User.objects.annotate(
            exam_count=Count('exam_attempts'),
            avg_score=Avg('exam_attempts__total_score'),
            review_count=Count('review_schedules'),
        ).filter(is_active=True).order_by('-exam_count')[:20]
        
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
            
            user_stats.append({
                'username': u.username,
                'first_name': u.first_name,
                'last_login': u.last_login,
                'exam_count': u.exam_count,
                'avg_score': u.avg_score,
                'review_count': u.review_count,
                'last_activity_type': last_activity_type,
                'last_activity_time': last_activity_time,
            })
        
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
