from django.contrib import admin
from django import forms
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
    
    formfield_overrides = {
        # CharField 필드를 120자 너비로 변경
        forms.CharField: {'widget': forms.TextInput(attrs={'size': '120'})},
    }
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        # content, choice1~5 필드를 Textarea로 변경
        if db_field.name in ['content', 'choice1', 'choice2', 'choice3', 'choice4', 'choice5']:
            kwargs['widget'] = forms.Textarea(attrs={'rows': 3, 'cols': 100})
        return super().formfield_for_dbfield(db_field, request, **kwargs)


@admin.register(UserExamAttempt)
class UserExamAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "exam", "start_time", "end_time", "total_score")
    list_filter = ("exam", "start_time")
    search_fields = ("user__username",)


@admin.register(UserQuestionResult)
class UserQuestionResultAdmin(admin.ModelAdmin):
    list_display = ("attempt", "question", "selected_choice", "is_correct")
    list_filter = ("is_correct",)
