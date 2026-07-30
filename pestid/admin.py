from django.contrib import admin
from django.utils.html import format_html

from .models import PestAttempt, PestCourse, PestQuestion


@admin.register(PestCourse)
class PestCourseAdmin(admin.ModelAdmin):
    list_display = ("name", "question_count", "order", "is_active", "created_at")
    list_editable = ("order", "is_active")
    search_fields = ("name",)


@admin.register(PestQuestion)
class PestQuestionAdmin(admin.ModelAdmin):
    list_display = ("thumb", "course", "order", "name", "occurrence", "overwinter", "host")
    list_filter = ("course",)
    search_fields = ("name", "host", "overwinter")
    list_select_related = ("course",)

    @admin.display(description="사진")
    def thumb(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:48px;border-radius:4px;">', obj.image.url
            )
        return "-"


@admin.register(PestAttempt)
class PestAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "mode", "correct_count", "total_count", "score_percent", "finished_at")
    list_filter = ("course", "mode")
    search_fields = ("user__username", "user__first_name")
    list_select_related = ("user", "course")
