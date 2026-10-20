from django.contrib import admin

from .models import PollResponse


@admin.register(PollResponse)
class PollResponseAdmin(admin.ModelAdmin):
    list_display = ("name", "age", "score", "level", "submitted_at", "ip")
    list_filter = ("level",)
    search_fields = ("name",)
    readonly_fields = ("score", "level", "submitted_at", "ip")
