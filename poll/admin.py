from django.contrib import admin

from .models import PollResponse


@admin.register(PollResponse)
class PollResponseAdmin(admin.ModelAdmin):
    list_display = ("name", "age_group", "frequency", "self_level", "score", "created_at")
    list_filter = ("age_group", "frequency", "created_at")
    search_fields = ("name", "want_to_learn")
