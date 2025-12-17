from django.contrib import admin
from .models import ChatHistory


@admin.register(ChatHistory)
class ChatHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "user_input", "formatted_created_at", "is_success")
    list_filter = ("created_at", "is_success")
    search_fields = ("user_input", "ai_response")
    list_per_page = 10

    def formatted_created_at(self, obj):
        return obj.created_at.strftime("%y/%m/%d")

    formatted_created_at.short_description = "작성일시"
    formatted_created_at.admin_order_field = "created_at"
