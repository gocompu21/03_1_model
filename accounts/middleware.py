"""세션 활동 추적 미들웨어"""
from django.utils import timezone
from .models import UserSession


class SessionTrackingMiddleware:
    """사용자 세션 활동을 추적하는 미들웨어"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 세션 만료 감지: 세션 쿠키는 있지만 인증되지 않은 경우
        session_expired = False
        session_key_from_cookie = request.COOKIES.get('sessionid')
        
        if session_key_from_cookie and not request.user.is_authenticated:
            # 세션이 만료된 경우 - 해당 세션 기록 종료
            expired_sessions = UserSession.objects.filter(
                session_key=session_key_from_cookie,
                logout_time__isnull=True
            )
            if expired_sessions.exists():
                expired_sessions.update(logout_time=timezone.now())
                session_expired = True
        
        # 요청 처리
        response = self.get_response(request)
        
        # 로그인된 사용자의 세션 활동 업데이트
        if request.user.is_authenticated and request.session.session_key:
            try:
                session = UserSession.objects.filter(
                    user=request.user,
                    session_key=request.session.session_key,
                    logout_time__isnull=True
                ).first()
                
                if session:
                    # last_activity 업데이트 (auto_now 필드는 save()로 자동 업데이트)
                    session.save(update_fields=['last_activity'])
            except Exception:
                pass  # 에러 발생 시 무시
        
        return response
