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
        """사용자의 오늘 체류시간 (초)

        오늘 활동이 있는 모든 세션에서 오늘에 해당하는 시간만 계산.
        - 어제 로그인 → 오늘 활동: 오늘 자정부터 마지막 활동까지만 계산
        - 오늘 로그인: 로그인 시간부터 계산
        """
        import datetime
        today = timezone.now().date()
        today_start = timezone.make_aware(
            datetime.datetime.combine(today, datetime.time.min)
        )
        now = timezone.now()

        # 오늘 활동이 있는 세션: 오늘 로그인했거나, 마지막 활동이 오늘인 경우
        sessions = cls.objects.filter(user=user).filter(
            models.Q(login_time__date=today) |
            models.Q(last_activity__date=today)
        )

        total = 0
        for s in sessions:
            # 시작 시간: 로그인 시간 또는 오늘 자정 중 더 늦은 시간
            start = max(s.login_time, today_start)
            # 종료 시간: 로그아웃 시간 또는 마지막 활동 시간
            end = s.logout_time or s.last_activity

            # 오늘 범위 내의 시간만 계산
            if end >= today_start:
                duration = (end - start).total_seconds()
                if duration > 0:
                    total += duration

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
    
    @property
    def device_type(self):
        """User-Agent에서 기기 종류 파싱"""
        ua = self.user_agent.lower()
        if 'ipad' in ua:
            return 'iPad'
        elif 'iphone' in ua:
            return 'iPhone'
        elif 'android' in ua:
            if 'mobile' in ua:
                return 'Android폰'
            else:
                return 'Android태블릿'
        elif 'macintosh' in ua or 'mac os' in ua:
            return 'Mac'
        elif 'windows' in ua:
            return 'Windows'
        else:
            return '기타'
    
    @property
    def device_icon(self):
        """기기 종류에 맞는 Font Awesome 아이콘 클래스"""
        device = self.device_type
        icons = {
            'iPad': 'fas fa-tablet-alt',
            'iPhone': 'fas fa-mobile-alt',
            'Android폰': 'fas fa-mobile-alt',
            'Android태블릿': 'fas fa-tablet-alt',
            'Mac': 'fas fa-laptop',
            'Windows': 'fas fa-desktop',
            '기타': 'fas fa-globe',
        }
        return icons.get(device, 'fas fa-globe')
