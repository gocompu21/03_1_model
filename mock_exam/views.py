from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import MockExam, MockExamQuestion
from exam.models import Question, Subject, Exam, UserExamAttempt, UserQuestionResult
from mypage.models import ReviewSchedule
import random


@login_required
def index(request):
    """
    Mock Exam Dashboard
    """
    recent_exams = MockExam.objects.filter(user=request.user).order_by("-start_time")[
        :5
    ]
    return render(request, "mock_exam/index.html", {"recent_exams": recent_exams})


@login_required
def generate_mock_exam(request):
    """
    Generate a new random mock exam with 125 questions (25 per subject)
    Order: 수목병리학 -> 수목해충학 -> 수목생리학 -> 산림토양학 -> 수목관리학

    Questions not yet attempted in previous mock exams have higher weight.
    """
    target_subjects = [
        "수목병리학",
        "수목해충학",
        "수목생리학",
        "산림토양학",
        "수목관리학",
    ]
    selected_questions = []

    # Get IDs of questions this user has already attempted in mock exams
    attempted_question_ids = set(
        MockExamQuestion.objects.filter(
            mock_exam__user=request.user, mock_exam__is_completed=True
        ).values_list("question_id", flat=True)
    )

    for subject_name in target_subjects:
        try:
            subject = Subject.objects.get(name=subject_name)
            questions = list(Question.objects.filter(subject=subject))

            if len(questions) == 0:
                continue

            # Create weights: unseen questions get weight 3, attempted get weight 1
            weights = []
            for q in questions:
                if q.id in attempted_question_ids:
                    weights.append(1)  # Lower weight for seen questions
                else:
                    weights.append(3)  # Higher weight for unseen questions

            # Select 25 questions using weighted random choices (without replacement)
            num_to_select = min(25, len(questions))

            # Use weighted selection without replacement
            selected = []
            available = list(zip(questions, weights))
            for _ in range(num_to_select):
                if not available:
                    break
                # Normalize weights
                total_weight = sum(w for _, w in available)
                if total_weight == 0:
                    break

                # Weighted random choice
                r = random.uniform(0, total_weight)
                cumulative = 0
                for i, (q, w) in enumerate(available):
                    cumulative += w
                    if r <= cumulative:
                        selected.append(q)
                        available.pop(i)
                        break

            selected_questions.extend(selected)

        except Subject.DoesNotExist:
            continue  # Skip if subject doesn't exist

    if not selected_questions:
        # Handle case with no questions in DB
        return render(
            request,
            "mock_exam/index.html",
            {"error": "등록된 문제가 충분하지 않습니다."},
        )

    # Create Mock Exam Session
    mock_exam = MockExam.objects.create(user=request.user)

    # Create Relations (Bulk Create)
    mock_questions = [
        MockExamQuestion(mock_exam=mock_exam, question=q) for q in selected_questions
    ]
    MockExamQuestion.objects.bulk_create(mock_questions)

    return redirect("mock_exam:take", pk=mock_exam.pk)


@login_required
def take_exam(request, pk):
    """
    Take the exam view
    """
    mock_exam = get_object_or_404(MockExam, pk=pk, user=request.user)

    if mock_exam.is_completed:
        return redirect("mock_exam:result", pk=pk)

    questions = mock_exam.questions.select_related("question").all()

    return render(
        request,
        "mock_exam/take_v2.html",
        {"mock_exam": mock_exam, "questions": questions},
    )


@login_required
def submit_exam(request, pk):
    """
    Grade and submit the exam
    """
    mock_exam = get_object_or_404(MockExam, pk=pk, user=request.user)

    if request.method == "POST":
        questions = mock_exam.questions.select_related("question").all()
        correct_count = 0

        for mq in questions:
            # Get user answer from form data
            # Form input name format: question_{mq.id}
            user_choice = request.POST.get(f"question_{mq.id}")

            if user_choice:
                mq.selected_choice = int(user_choice)
                if mq.selected_choice == mq.question.answer:
                    mq.is_correct = True
                    correct_count += 1
                else:
                    mq.is_correct = False
                mq.save()

        # specific scoring logic: simple percentage or count for now
        # Tree Doctor exam: 100 questions, but we might have fewer
        total = questions.count()
        score = (correct_count / total * 100) if total > 0 else 0

        mock_exam.score = int(score)
        mock_exam.end_time = timezone.now()
        mock_exam.is_completed = True
        mock_exam.save()

        # --- Integration with MyPage History and Wrong Answer Notes ---
        # Get or create a "virtual" Exam for Mock Exams (round_number=0)
        virtual_exam, _ = Exam.objects.get_or_create(
            round_number=0, defaults={"round_number": 0}
        )

        # Create UserExamAttempt for this mock exam submission
        user_attempt = UserExamAttempt.objects.create(
            user=request.user,
            exam=virtual_exam,
            end_time=mock_exam.end_time,
            total_score=correct_count,
        )

        # Add all subjects involved in this mock exam
        subject_ids = questions.values_list("question__subject", flat=True).distinct()
        user_attempt.subjects.set(subject_ids)

        # Create UserQuestionResult for each question
        user_results = []
        for mq in questions:
            if mq.selected_choice is not None:
                user_results.append(
                    UserQuestionResult(
                        attempt=user_attempt,
                        question=mq.question,
                        selected_choice=mq.selected_choice,
                        is_correct=mq.is_correct,
                    )
                )
        UserQuestionResult.objects.bulk_create(user_results)
        # --- End Integration ---

        # --- Smart Review Schedule Integration ---
        for mq in questions:
            if mq.selected_choice is not None and not mq.is_correct:
                # Create or update review schedule for wrong answers
                review_schedule, created = ReviewSchedule.objects.get_or_create(
                    user=request.user,
                    question=mq.question,
                    defaults={
                        "last_wrong_date": timezone.now(),
                        "review_count": 0,
                        "next_review_date": timezone.now().date(),
                        "is_mastered": False,
                    },
                )
                if not created:
                    # Reset review count if answered wrong again
                    review_schedule.review_count = 0
                    review_schedule.last_wrong_date = timezone.now()
                    review_schedule.is_mastered = False
                    review_schedule.next_review_date = (
                        review_schedule.calculate_next_review_date()
                    )
                    review_schedule.save()
        # --- End Smart Review ---

        return redirect("mock_exam:result", pk=pk)

    return redirect("mock_exam:take", pk=pk)


@login_required
def result_exam(request, pk):
    """
    Show exam result
    """
    mock_exam = get_object_or_404(MockExam, pk=pk, user=request.user)

    if not mock_exam.is_completed:
        return redirect("mock_exam:take", pk=pk)

    questions = mock_exam.questions.select_related("question").all()

    return render(
        request,
        "mock_exam/result.html",
        {"mock_exam": mock_exam, "questions": questions},
    )
