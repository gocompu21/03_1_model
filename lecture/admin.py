from django.contrib import admin

from .models import Lecture, LectureView


@admin.register(Lecture)
class LectureAdmin(admin.ModelAdmin):
    list_display = ("lecture_date", "subject", "period", "title", "duration_min", "is_active")
    list_filter = ("subject", "is_active", "lecture_date")
    search_fields = ("title", "note")
    date_hierarchy = "lecture_date"


@admin.register(LectureView)
class LectureViewAdmin(admin.ModelAdmin):
    list_display = ("user", "lecture", "count", "first_viewed_at", "last_viewed_at")
    list_filter = ("lecture__subject", "last_viewed_at")
    search_fields = ("user__username", "user__first_name", "lecture__title")
