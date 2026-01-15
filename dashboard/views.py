from django.shortcuts import render, get_object_or_404, redirect
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
    from exam.models import Exam
    
    books = Book.objects.all().order_by('subject', 'name')
    exams = Exam.objects.all().order_by('round_number')
    
    context = {
        'books': books,
        'exams': exams,
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


@login_required
@staff_member_required
def get_exam_questions(request):
    """특정 회차의 문제 목록 반환 (JSON)"""
    from django.http import JsonResponse
    from exam.models import Question
    
    exam_id = request.GET.get('exam_id')
    if not exam_id:
        return JsonResponse({'questions': []})
        
    questions = Question.objects.filter(exam_id=exam_id).select_related('subject').order_by('number')
    
    data = []
    for q in questions:
        data.append({
            'id': q.id,
            'number': q.number,
            'subject': q.subject.name,
            'full_text': f"{q.number}번 - [{q.subject.name}]"
        })
        
    return JsonResponse({'questions': data})


@login_required
@staff_member_required
def exam_pdf(request):
    """선택한 기출문제 인쇄 페이지"""
    from exam.models import Question, Exam
    
    if request.method == 'POST':
        question_ids = request.POST.getlist('question_ids')
        # exam_id는 이제 필수가 아님 (여러 회차가 섞일 수 있음)
    else:
        # GET으로 넘어온 경우 (거의 없겠지만)
        return render(request, 'dashboard/print.html')
        
    if not question_ids:
        # 혹시 쉼표로 구분된 문자열로 넘어올 경우 처리 (JS에서 hidden input으로 넘길 때)
        question_ids_str = request.POST.get('question_ids_str')
        if question_ids_str:
            question_ids = question_ids_str.split(',')
            
    if not question_ids:
        return HttpResponse('선택된 문제가 없습니다.', status=400)
    
    # 문제 조회
    # filter(id__in=...)은 순서를 보장하지 않음
    questions_queryset = Question.objects.filter(id__in=question_ids).select_related('exam', 'subject')
    
    # 사용자가 담은 순서(=question_ids 순서)대로 정렬하기 위해 딕셔너리 매핑
    questions_dict = {str(q.id): q for q in questions_queryset}
    
    # 리스트 컴프리헨션으로 순서 유지하여 리스트 생성
    questions = []
    for q_id in question_ids:
        if str(q_id) in questions_dict:
            questions.append(questions_dict[str(q_id)])
            
    custom_title = request.POST.get('custom_title', '').strip()
    
    return render(request, 'dashboard/exam_pdf.html', {
        'questions': questions,
        'is_multi_exam': True,
        'custom_title': custom_title
    })


@login_required
@staff_member_required
def save_topic_set(request):
    """주제별 문제집 저장 (AJAX)"""
    from django.http import JsonResponse
    from exam.models import TopicQuestionSet, TopicQuestionSetItem, Question
    import json
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'}, status=400)
    
    try:
        data = json.loads(request.body)
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        question_ids = data.get('question_ids', [])
        
        if not title:
            return JsonResponse({'success': False, 'error': '제목을 입력해주세요.'})
        
        if not question_ids:
            return JsonResponse({'success': False, 'error': '문제를 선택해주세요.'})
        
        # 문제집 생성
        topic_set = TopicQuestionSet.objects.create(
            title=title,
            description=description,
            created_by=request.user,
            is_public=True
        )
        
        # 문제 추가 (순서 유지)
        for order, question_id in enumerate(question_ids, start=1):
            try:
                question = Question.objects.get(id=question_id)
                TopicQuestionSetItem.objects.create(
                    question_set=topic_set,
                    question=question,
                    order=order
                )
            except Question.DoesNotExist:
                pass  # 문제가 없으면 스킵
        
        return JsonResponse({'success': True, 'topic_set_id': topic_set.id})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def topic_set_list(request):
    """주제별 문제집 목록"""
    from exam.models import TopicQuestionSet
    
    topic_sets = TopicQuestionSet.objects.filter(is_public=True).prefetch_related('items').order_by('-created_at')
    
    return render(request, 'dashboard/topic_set_list.html', {
        'topic_sets': topic_sets
    })


@login_required
def topic_set_solve(request, set_id):
    """주제별 문제집 풀이"""
    from exam.models import TopicQuestionSet, UserTopicSetAttempt, UserTopicQuestionResult
    from django.utils import timezone
    
    topic_set = get_object_or_404(TopicQuestionSet, id=set_id)
    
    # 문제 가져오기 (순서대로)
    items = topic_set.items.select_related('question__exam', 'question__subject').order_by('order')
    questions = [item.question for item in items]
    
    if request.method == 'POST':
        # 채점 및 결과 저장
        attempt = UserTopicSetAttempt.objects.create(
            user=request.user,
            question_set=topic_set
        )
        
        correct_count = 0
        for q in questions:
            selected_choice = request.POST.get(f'question_{q.id}')
            if selected_choice:
                selected_choice = int(selected_choice)
                is_correct = selected_choice in q.answer
                if is_correct:
                    correct_count += 1
                
                UserTopicQuestionResult.objects.create(
                    attempt=attempt,
                    question=q,
                    selected_choice=selected_choice,
                    is_correct=is_correct
                )
                
                # 오답 시 복습 스케줄 등록
                if not is_correct:
                    from mypage.models import ReviewSchedule
                    
                    review_schedule, created = ReviewSchedule.objects.get_or_create(
                        user=request.user,
                        question=q,
                        defaults={
                            'last_wrong_date': timezone.now(),
                            'review_count': 0,
                            'next_review_date': timezone.localdate(),
                            'is_mastered': False,
                        }
                    )
                    if not created:
                        review_schedule.review_count = 0
                        review_schedule.last_wrong_date = timezone.now()
                        review_schedule.is_mastered = False
                        review_schedule.next_review_date = review_schedule.calculate_next_review_date()
                        review_schedule.save()
        
        attempt.total_score = correct_count
        attempt.end_time = timezone.now()
        attempt.save()
        
        return redirect('dashboard:topic_set_result', attempt_id=attempt.id)
    
    # study/detail.html과 호환을 위해 변수 이름 맞추기
    return render(request, 'dashboard/topic_set_solve.html', {
        'topic_set': topic_set,
        'exam': topic_set,  # 템플릿 호환성
        'round_number': topic_set.title,  # 제목을 회차처럼 표시
        'questions': questions
    })


@login_required
def topic_set_result(request, attempt_id):
    """주제별 문제집 결과"""
    from exam.models import UserTopicSetAttempt, UserTopicQuestionResult
    
    attempt = get_object_or_404(UserTopicSetAttempt, id=attempt_id)
    results = UserTopicQuestionResult.objects.filter(attempt=attempt).select_related('question__exam', 'question__subject')
    
    total_attempted = results.count()
    score_100 = (attempt.total_score / total_attempted * 100) if total_attempted > 0 else 0
    
    return render(request, 'dashboard/topic_set_result.html', {
        'attempt': attempt,
        'results': results,
        'score_100': score_100,
        'total_attempted': total_attempted
    })
