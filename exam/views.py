from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Exam, Subject, Question, UserExamAttempt, UserQuestionResult
from .forms import QuestionForm


@login_required
def exam_list(request):
    exams = Exam.objects.all().order_by("round_number")
    subjects = Subject.objects.all().order_by("code")
    return render(
        request, "exam/exam_list.html", {"exams": exams, "subjects": subjects}
    )


def exam_take(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    selected_subject_codes = request.GET.getlist("subjects")
    if selected_subject_codes:
        questions = Question.objects.filter(
            exam=exam, subject__code__in=selected_subject_codes
        )
    else:
        questions = Question.objects.filter(exam=exam)

    return render(
        request,
        "exam/exam_take.html",
        {
            "exam": exam,
            "questions": questions,
            "selected_subjects": selected_subject_codes,
            "is_retry": False,
        },
    )


def exam_submit(request, exam_id):
    if request.method == "POST":
        exam = get_object_or_404(Exam, id=exam_id)
        if request.user.is_authenticated:
            user = request.user
        else:
            from django.contrib.auth.models import User

            user, created = User.objects.get_or_create(username="guest")

        attempt = UserExamAttempt.objects.create(user=user, exam=exam)

        questions = Question.objects.filter(exam=exam)
        correct_count = 0

        for q in questions:
            selected_choice = request.POST.get(f"question_{q.id}")
            if selected_choice:
                selected_choice = int(selected_choice)
                is_correct = selected_choice == q.answer
                if is_correct:
                    correct_count += 1

                UserQuestionResult.objects.create(
                    attempt=attempt,
                    question=q,
                    selected_choice=selected_choice,
                    is_correct=is_correct,
                )

        attempt.total_score = correct_count
        attempt.save()

        return redirect("exam:result", attempt_id=attempt.id)
    return redirect("exam:index")


def exam_result(request, attempt_id):
    attempt = get_object_or_404(UserExamAttempt, id=attempt_id)
    results = UserQuestionResult.objects.filter(attempt=attempt).select_related(
        "question"
    )
    return render(
        request, "exam/exam_result.html", {"attempt": attempt, "results": results}
    )


def retry_exam(request, attempt_id):
    original_attempt = get_object_or_404(UserExamAttempt, id=attempt_id)
    wrong_results = UserQuestionResult.objects.filter(
        attempt=original_attempt, is_correct=False
    )
    wrong_question_ids = wrong_results.values_list("question_id", flat=True)
    questions = Question.objects.filter(id__in=wrong_question_ids)

    return render(
        request,
        "exam/exam_take.html",
        {"exam": original_attempt.exam, "questions": questions, "is_retry": True},
    )


def question_list(request):
    questions = Question.objects.all().select_related("exam", "subject").order_by("-id")
    return render(request, "exam/question_list.html", {"questions": questions})


def question_create(request):
    if request.method == "POST":
        form = QuestionForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("exam:question_list")
    else:
        form = QuestionForm()
    return render(request, "exam/question_form.html", {"form": form})


def question_update(request, pk):
    question = get_object_or_404(Question, pk=pk)
    if request.method == "POST":
        form = QuestionForm(request.POST, request.FILES, instance=question)
        if form.is_valid():
            form.save()
            return redirect("exam:question_list")
    else:
        form = QuestionForm(instance=question)
    return render(request, "exam/question_form.html", {"form": form})


def question_delete(request, pk):
    question = get_object_or_404(Question, pk=pk)
    if request.method == "POST":
        question.delete()
        return redirect("exam:question_list")
    return render(request, "exam/question_confirm_delete.html", {"question": question})
