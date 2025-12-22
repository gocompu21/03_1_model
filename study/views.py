from django.shortcuts import render, get_object_or_404
from exam.models import Exam, Question, Subject
from django.contrib.auth.decorators import login_required


@login_required
def index(request):
    """
    List all available exam rounds and subjects.
    """
    exams = Exam.objects.exclude(round_number=0).order_by("round_number")
    subjects = Subject.objects.all().order_by("code")
    return render(request, "study/index.html", {"exams": exams, "subjects": subjects})


def detail(request, round_number):
    """
    Show all questions for a specific round.
    """
    # Get the exam object for context (title etc)
    # Using filter().first() or get_object_or_404 if we want to be strict
    # But wait, Question checks round_number via exam__round_number?
    # Or is Exam object keys by round_number?

    # Let's verify Exam model structure first.
    # Proceeding with assumption: Exam has round_number field.

    exam = Exam.objects.filter(round_number=round_number).first()

    # Get all questions
    questions = Question.objects.filter(exam__round_number=round_number).order_by(
        "number"
    )

    context = {"round_number": round_number, "exam": exam, "questions": questions}
    return render(request, "study/detail.html", context)


def subject_detail(request, subject_name):
    """
    Show questions for a specific subject, filtered by round (via query param).
    Default to first available round if not specified.
    """
    # 1. Get All Exams for Tabs
    exams = Exam.objects.exclude(round_number=0).order_by("round_number")

    # 2. Determine Round Number
    round_param = request.GET.get("round")
    if round_param:
        try:
            current_round = int(round_param)
        except ValueError:
            current_round = exams.first().round_number if exams.exists() else 0
    else:
        # Default to first round
        current_round = exams.first().round_number if exams.exists() else 0

    # 3. Filter Questions
    # Note: Subject name might need decoding if passed in URL but Django handles unicode in URL params usually.
    questions = Question.objects.filter(
        subject__name=subject_name, exam__round_number=current_round
    ).order_by("number")

    context = {
        "subject_name": subject_name,
        "current_round": current_round,
        "exams": exams,
        "questions": questions,
    }
    return render(request, "study/study_by_subject.html", context)
