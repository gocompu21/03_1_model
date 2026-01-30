from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import (
    Exam,
    Subject,
    Question,
    UserExamAttempt,
    UserQuestionResult,
    TopicQuestionSet,
)
from .serializers import (
    ExamListSerializer,
    SubjectSerializer,
    QuestionListSerializer,
    QuestionDetailSerializer,
    ExamSubmitSerializer,
    UserExamAttemptListSerializer,
    UserExamAttemptDetailSerializer,
    TopicQuestionSetListSerializer,
    TopicQuestionSetDetailSerializer,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def exam_list(request):
    """
    시험 목록 조회
    GET /api/exam/
    """
    exams = Exam.objects.all().order_by("-round_number")
    serializer = ExamListSerializer(exams, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subject_list(request):
    """
    과목 목록 조회
    GET /api/exam/subjects/
    """
    subjects = Subject.objects.all().order_by("code")
    serializer = SubjectSerializer(subjects, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def exam_detail(request, exam_id):
    """
    시험 상세 정보 (과목별 문제 수 등)
    GET /api/exam/<exam_id>/
    """
    exam = get_object_or_404(Exam, id=exam_id)
    subjects = Subject.objects.all()

    data = {
        "id": exam.id,
        "round_number": exam.round_number,
        "subjects": [],
    }

    for subject in subjects:
        question_count = Question.objects.filter(exam=exam, subject=subject).count()
        if question_count > 0:
            data["subjects"].append({
                "id": subject.id,
                "name": subject.name,
                "code": subject.code,
                "question_count": question_count,
            })

    return Response(data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def exam_start(request, exam_id):
    """
    시험 시작 - 응시 기록 생성 및 문제 반환
    POST /api/exam/<exam_id>/start/
    Body: {"subject_ids": [1, 2, 3]}  # 선택한 과목 ID 목록
    """
    exam = get_object_or_404(Exam, id=exam_id)
    subject_ids = request.data.get("subject_ids", [])

    if not subject_ids:
        return Response(
            {"error": "과목을 선택해주세요."},
            status=status.HTTP_400_BAD_REQUEST
        )

    subjects = Subject.objects.filter(id__in=subject_ids)
    if not subjects.exists():
        return Response(
            {"error": "유효하지 않은 과목입니다."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 응시 기록 생성
    attempt = UserExamAttempt.objects.create(user=request.user, exam=exam)
    attempt.subjects.set(subjects)

    # 해당 과목의 문제 조회
    questions = Question.objects.filter(
        exam=exam,
        subject__in=subjects
    ).order_by("number")

    serializer = QuestionListSerializer(
        questions,
        many=True,
        context={"request": request}
    )

    return Response({
        "attempt_id": attempt.id,
        "exam_round": exam.round_number,
        "questions": serializer.data,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def exam_submit(request, attempt_id):
    """
    시험 제출 - 답안 채점 및 결과 저장
    POST /api/exam/submit/<attempt_id>/
    Body: {"answers": [{"question_id": 1, "selected_choice": 3}, ...]}
    """
    attempt = get_object_or_404(
        UserExamAttempt,
        id=attempt_id,
        user=request.user
    )

    if attempt.end_time:
        return Response(
            {"error": "이미 제출된 시험입니다."},
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer = ExamSubmitSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    answers = serializer.validated_data["answers"]
    correct_count = 0
    total_count = len(answers)

    for answer in answers:
        question = get_object_or_404(Question, id=answer["question_id"])
        selected = answer["selected_choice"]

        # 정답 체크 (answer가 리스트이므로 포함 여부 확인)
        is_correct = selected in question.answer

        UserQuestionResult.objects.create(
            attempt=attempt,
            question=question,
            selected_choice=selected,
            is_correct=is_correct,
        )

        if is_correct:
            correct_count += 1

    # 점수 계산 및 저장
    score = round((correct_count / total_count) * 100) if total_count > 0 else 0
    attempt.end_time = timezone.now()
    attempt.total_score = score
    attempt.save()

    return Response({
        "attempt_id": attempt.id,
        "total_score": score,
        "correct_count": correct_count,
        "total_count": total_count,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def exam_result(request, attempt_id):
    """
    시험 결과 조회
    GET /api/exam/result/<attempt_id>/
    """
    attempt = get_object_or_404(
        UserExamAttempt,
        id=attempt_id,
        user=request.user
    )

    serializer = UserExamAttemptDetailSerializer(
        attempt,
        context={"request": request}
    )
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_attempts(request):
    """
    내 시험 응시 기록 목록
    GET /api/exam/my-attempts/
    """
    attempts = UserExamAttempt.objects.filter(
        user=request.user
    ).order_by("-start_time")

    serializer = UserExamAttemptListSerializer(attempts, many=True)
    return Response(serializer.data)


# 주제별 문제집 API
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def topic_set_list(request):
    """
    주제별 문제집 목록
    GET /api/exam/topic-sets/
    """
    topic_sets = TopicQuestionSet.objects.filter(
        is_public=True
    ).order_by("order", "-created_at")

    serializer = TopicQuestionSetListSerializer(topic_sets, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def topic_set_detail(request, set_id):
    """
    주제별 문제집 상세 (문제 목록 포함)
    GET /api/exam/topic-sets/<set_id>/
    """
    topic_set = get_object_or_404(TopicQuestionSet, id=set_id, is_public=True)
    serializer = TopicQuestionSetDetailSerializer(
        topic_set,
        context={"request": request}
    )
    return Response(serializer.data)
