from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.db.models import Count, Avg, Case, When, IntegerField
from django.utils import timezone

from exam.models import UserQuestionResult, UserExamAttempt, Subject


@login_required
@staff_member_required
def index(request):
    """Admin Dashboard - 관리자 대시보드 메인"""
    from study.models import StudyViewLog
    from accounts.models import UserSession
    from mypage.models import ReviewSchedule
    
    # User Statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    users_with_attempts = UserExamAttempt.objects.values('user').distinct().count()
    
    # User performance data with stats
    user_stats = []
    for user in User.objects.filter(is_active=True).exclude(is_superuser=True):
        exam_count = UserExamAttempt.objects.filter(user=user).count()
        study_count = StudyViewLog.objects.filter(user=user).count()
        avg_score = UserExamAttempt.objects.filter(user=user).aggregate(
            avg=Avg('total_score')
        )['avg']
        review_count = ReviewSchedule.objects.filter(user=user, is_mastered=False).count()
        
        # Session duration (in minutes)
        today_minutes = UserSession.get_user_today_duration(user) // 60
        total_minutes = UserSession.get_user_total_duration(user) // 60
        
        # Format as H:MM
        def format_duration(minutes):
            minutes = int(minutes)
            if minutes == 0:
                return "-"
            h = minutes // 60
            m = minutes % 60
            return f"{h}:{m:02d}"
        
        # Last activity
        last_session = UserSession.objects.filter(user=user).order_by('-login_time').first()
        
        # Check if user is currently online (active session within last 30 minutes)
        from datetime import timedelta
        is_online = False
        if last_session and last_session.logout_time is None:
            # Session without logout is potentially active, check last_activity
            time_since_last_activity = timezone.now() - last_session.last_activity
            is_online = time_since_last_activity < timedelta(minutes=30)
        
        user_stats.append({
            'username': user.username,
            'first_name': user.first_name,
            'exam_count': exam_count,
            'study_count': study_count,
            'avg_score': avg_score,
            'review_count': review_count,
            'today_duration': format_duration(today_minutes),
            'total_duration': format_duration(total_minutes),
            'total_minutes_raw': total_minutes,  # For sorting
            'is_online': is_online,
            'last_logout_time': last_session.logout_time if last_session else None,
            'last_activity_time': last_session.login_time if last_session else None,
            'last_activity_type': '로그인' if last_session else '-',
        })
    
    # Sort by total duration (descending)
    user_stats.sort(key=lambda x: x['total_minutes_raw'], reverse=True)
    
    # Subject performance stats
    subject_stats = []
    for subject in Subject.objects.all():
        results = UserQuestionResult.objects.filter(question__subject=subject)
        total = results.count()
        correct = results.filter(is_correct=True).count()
        if total > 0:
            subject_stats.append({
                'name': subject.name,
                'avg_correct_rate': round((correct / total) * 100, 1),
                'total_attempts': total,
            })
    subject_stats.sort(key=lambda x: x['avg_correct_rate'])
    
    admin_dashboard = {
        'total_users': total_users,
        'active_users': active_users,
        'users_with_attempts': users_with_attempts,
        'user_stats': user_stats,
        'subject_stats': subject_stats,
    }
    
    context = {
        'admin_dashboard': admin_dashboard,
    }
    return render(request, 'dashboard/index.html', context)
