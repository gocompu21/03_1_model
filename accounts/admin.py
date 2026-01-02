from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Sum
from django.utils import timezone
from django.utils.html import format_html
from .models import UserSession


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'login_time', 'last_activity', 'logout_time', 'duration_display', 'ip_address', 'is_active_display')
    list_filter = ('user', 'login_time')
    search_fields = ('user__username', 'user__first_name', 'ip_address')
    readonly_fields = ('user', 'session_key', 'login_time', 'last_activity', 'logout_time', 'ip_address', 'user_agent')
    ordering = ('-login_time',)
    
    def duration_display(self, obj):
        return obj.duration_formatted
    duration_display.short_description = '체류시간'
    
    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">●</span> 활성')
        return format_html('<span style="color: gray;">○</span> 종료')
    is_active_display.short_description = '상태'


class UserSessionInline(admin.TabularInline):
    model = UserSession
    extra = 0
    readonly_fields = ('session_key', 'login_time', 'last_activity', 'logout_time', 'duration_display', 'ip_address')
    can_delete = False
    max_num = 10
    ordering = ('-login_time',)
    
    def duration_display(self, obj):
        return obj.duration_formatted
    duration_display.short_description = '체류시간'
    
    def has_add_permission(self, request, obj=None):
        return False


class CustomUserAdmin(BaseUserAdmin):
    list_display = ('username', 'first_name', 'email', 'is_staff', 'today_duration', 'total_duration')
    inlines = [UserSessionInline]
    
    def today_duration(self, obj):
        """오늘 체류시간"""
        seconds = UserSession.get_user_today_duration(obj)
        return UserSession.format_duration(seconds)
    today_duration.short_description = '오늘 체류시간'
    
    def total_duration(self, obj):
        """누적 체류시간"""
        seconds = UserSession.get_user_total_duration(obj)
        return UserSession.format_duration(seconds)
    total_duration.short_description = '누적 체류시간'


# 기존 User admin 해제 후 커스텀 admin 등록
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
