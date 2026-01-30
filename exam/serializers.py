from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Exam,
    Subject,
    Question,
    UserExamAttempt,
    UserQuestionResult,
    TopicQuestionSet,
    TopicQuestionSetItem,
    UserTopicSetAttempt,
    UserTopicQuestionResult,
)


class SubjectSerializer(serializers.ModelSerializer):
    """과목 시리얼라이저"""

    class Meta:
        model = Subject
        fields = ["id", "name", "code"]


class ExamListSerializer(serializers.ModelSerializer):
    """시험 목록용 시리얼라이저"""
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = ["id", "round_number", "question_count"]

    def get_question_count(self, obj):
        return obj.questions.count()


class QuestionListSerializer(serializers.ModelSerializer):
    """문제 목록용 시리얼라이저 (답 제외)"""
    subject_name = serializers.CharField(source="subject.name", read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "number",
            "content",
            "image",
            "choice1",
            "choice2",
            "choice3",
            "choice4",
            "choice5",
            "subject_name",
            "summary",
        ]


class QuestionDetailSerializer(serializers.ModelSerializer):
    """문제 상세 시리얼라이저 (답 포함 - 제출 후)"""
    subject_name = serializers.CharField(source="subject.name", read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "number",
            "content",
            "image",
            "choice1",
            "choice2",
            "choice3",
            "choice4",
            "choice5",
            "answer",
            "general_chat",
            "textbook_chat",
            "infographic_image",
            "narration",
            "summary",
            "subject_name",
        ]


class AnswerSubmitSerializer(serializers.Serializer):
    """답안 제출 시리얼라이저"""
    question_id = serializers.IntegerField()
    selected_choice = serializers.IntegerField(min_value=1, max_value=5)


class ExamSubmitSerializer(serializers.Serializer):
    """시험 제출 시리얼라이저"""
    answers = AnswerSubmitSerializer(many=True)


class UserQuestionResultSerializer(serializers.ModelSerializer):
    """문제별 결과 시리얼라이저"""
    question = QuestionDetailSerializer(read_only=True)

    class Meta:
        model = UserQuestionResult
        fields = ["id", "question", "selected_choice", "is_correct"]


class UserExamAttemptListSerializer(serializers.ModelSerializer):
    """시험 응시 목록 시리얼라이저"""
    exam_round = serializers.IntegerField(source="exam.round_number", read_only=True)
    subjects = SubjectSerializer(many=True, read_only=True)
    correct_count = serializers.SerializerMethodField()
    total_count = serializers.SerializerMethodField()

    class Meta:
        model = UserExamAttempt
        fields = [
            "id",
            "exam_round",
            "subjects",
            "start_time",
            "end_time",
            "total_score",
            "correct_count",
            "total_count",
        ]

    def get_correct_count(self, obj):
        return obj.results.filter(is_correct=True).count()

    def get_total_count(self, obj):
        return obj.results.count()


class UserExamAttemptDetailSerializer(serializers.ModelSerializer):
    """시험 응시 상세 시리얼라이저"""
    exam_round = serializers.IntegerField(source="exam.round_number", read_only=True)
    subjects = SubjectSerializer(many=True, read_only=True)
    results = UserQuestionResultSerializer(many=True, read_only=True)

    class Meta:
        model = UserExamAttempt
        fields = [
            "id",
            "exam_round",
            "subjects",
            "start_time",
            "end_time",
            "total_score",
            "ai_analysis",
            "results",
        ]


# 주제별 문제집 시리얼라이저
class TopicQuestionSetListSerializer(serializers.ModelSerializer):
    """주제별 문제집 목록"""
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    question_count = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = TopicQuestionSet
        fields = [
            "id",
            "title",
            "description",
            "subject_name",
            "question_count",
            "created_by_name",
            "created_at",
            "is_public",
        ]

    def get_question_count(self, obj):
        return obj.items.count()


class TopicQuestionSetDetailSerializer(serializers.ModelSerializer):
    """주제별 문제집 상세 (문제 포함)"""
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    questions = serializers.SerializerMethodField()

    class Meta:
        model = TopicQuestionSet
        fields = [
            "id",
            "title",
            "description",
            "subject_name",
            "created_at",
            "questions",
        ]

    def get_questions(self, obj):
        items = obj.items.select_related("question").order_by("order")
        return QuestionListSerializer([item.question for item in items], many=True).data
