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
        
        # Check if user is currently online (has active session with no logout_time)
        is_online = last_session and last_session.logout_time is None
        
        # Determine last activity type
        last_activity_type = ''
        if last_session:
            if last_session.logout_time:
                last_activity_type = '로그아웃'
            else:
                last_activity_type = '활동중'
        
        user_stats.append({
            'username': user.username,
            'first_name': user.first_name,
            'exam_count': exam_count,
            'study_count': study_count,
            'review_count': review_count,
            'today_duration': format_duration(today_minutes),
            'total_duration': format_duration(total_minutes),
            'total_minutes_raw': total_minutes,  # For sorting
            'is_online': is_online,
            'last_activity': last_session.last_activity if last_session else None,
            'last_activity_type': last_activity_type,
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


@login_required
@staff_member_required
def print_material(request):
    """자료 인쇄 페이지"""
    from practice.models import Book
    books = Book.objects.all().order_by('id')
    
    context = {
        'books': books,
        'page_title': '자료 인쇄'
    }
    return render(request, 'dashboard/print.html', context)


@login_required
@staff_member_required
def get_chapters(request):
    """특정 교재의 목차 목록 반환 (JSON)"""
    from django.http import JsonResponse
    from practice.models import Chapter
    
    book_id = request.GET.get('book_id')
    if not book_id:
        return JsonResponse({'chapters': []})
        
    # 모든 챕터를 가져와서 계층 구조 표시
    # code(1.2.3)를 기준으로 자연 정렬 (Natural Sort)
    chapters = Chapter.objects.filter(book_id=book_id).order_by('order')
    
    # Python에서 정렬
    def natural_key(ch):
        # "1.2.3" -> [1, 2, 3] 변환하여 튜플 비교
        import re
        return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', ch.code)]

    sorted_chapters = sorted(chapters, key=natural_key)
    
    data = []
    for ch in sorted_chapters:
        data.append({
            'id': ch.id,
            'code': ch.code,
            'title': ch.title,
            'level': ch.level,
            'full_text': f"{ch.code} {ch.title}"
        })
        
    return JsonResponse({'chapters': data})
