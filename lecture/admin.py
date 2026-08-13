from django.contrib import admin

from .models import Lecture


@admin.register(Lecture)
class LectureAdmin(admin.ModelAdmin):
    list_display = ("lecture_date", "subject", "period", "title", "duration_min", "is_active")
    list_filter = ("subject", "is_active", "lecture_date")
    search_fields = ("title", "note")
    date_hierarchy = "lecture_date"
