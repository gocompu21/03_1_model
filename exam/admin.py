from django.contrib import admin
from .models import Exam, Subject, Question, UserExamAttempt, UserQuestionResult


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("round_number",)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "code")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("exam", "subject", "number", "content", "answer")
    list_filter = ("exam", "subject")
    search_fields = ("content", "general_chat")
    ordering = ("exam", "subject", "number")


@admin.register(UserExamAttempt)
class UserExamAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "exam", "start_time", "end_time", "total_score")
    list_filter = ("exam", "start_time")
    search_fields = ("user__username",)


@admin.register(UserQuestionResult)
class UserQuestionResultAdmin(admin.ModelAdmin):
    list_display = ("attempt", "question", "selected_choice", "is_correct")
    list_filter = ("is_correct",)
