from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserSession(models.Model):
    """사용자 세션 추적 모델"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True)
    login_time = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    last_page_name = models.CharField(max_length=100, blank=True, default='', verbose_name="마지막 페이지")
    logout_time = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    
    class Meta:
        verbose_name = "사용자 세션"
        verbose_name_plural = "사용자 세션"
        ordering = ['-login_time']
    
    def __str__(self):
        return f"{self.user.username} - {self.login_time.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def duration_seconds(self):
        """체류시간 (초)"""
        end_time = self.logout_time or self.last_activity
        return (end_time - self.login_time).total_seconds()
    
    @property
    def duration_formatted(self):
        """체류시간 (포맷팅)"""
        seconds = int(self.duration_seconds)
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}시간 {minutes}분"
        elif minutes > 0:
            return f"{minutes}분 {seconds}초"
        else:
            return f"{seconds}초"
    
    @property
    def is_active(self):
        """현재 활성 세션인지 여부"""
        return self.logout_time is None
    
    @classmethod
    def get_user_total_duration(cls, user):
        """사용자의 누적 체류시간 (초)"""
        sessions = cls.objects.filter(user=user)
        total = sum(s.duration_seconds for s in sessions)
        return total
    
    @classmethod
    def get_user_today_duration(cls, user):
        """사용자의 오늘 체류시간 (초)"""
        today = timezone.now().date()
        sessions = cls.objects.filter(
            user=user,
            login_time__date=today
        )
        total = sum(s.duration_seconds for s in sessions)
        return total
    
    @classmethod
    def format_duration(cls, seconds):
        """초를 시:분:초 형식으로 변환"""
        seconds = int(seconds)
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}시간 {minutes}분"
        elif minutes > 0:
            return f"{minutes}분 {secs}초"
        else:
            return f"{secs}초"
