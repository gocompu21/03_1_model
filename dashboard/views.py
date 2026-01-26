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
    for user in User.objects.filter(is_active=True):
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
            'last_login': user.last_login,
            'last_logout': last_session.logout_time if last_session else None,
            'exam_count': exam_count,
            'study_count': study_count,
            'review_count': review_count,
            'today_duration': format_duration(today_minutes),
            'total_duration': format_duration(total_minutes),
            'total_minutes_raw': total_minutes,  # For sorting
            'is_online': is_online,
            'last_activity': last_session.last_activity if last_session else None,
            'last_page_name': last_session.last_page_name if last_session else '',
            'last_activity_type': last_activity_type,
            'device_type': last_session.device_type if last_session else '',
            'device_icon': last_session.device_icon if last_session else 'fas fa-globe',
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
    from exam.models import Exam, Subject
    
    books = Book.objects.all().order_by('subject', 'name')
    exams = Exam.objects.all().order_by('round_number')
    subjects = Subject.objects.all().order_by('code')
    
    context = {
        'books': books,
        'exams': exams,
        'subjects': subjects,
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
        subject_id = data.get('subject_id')
        
        if not title:
            return JsonResponse({'success': False, 'error': '제목을 입력해주세요.'})
        
        if not question_ids:
            return JsonResponse({'success': False, 'error': '문제를 선택해주세요.'})
        
        # 과목 가져오기
        from exam.models import Subject
        subject = None
        if subject_id:
            try:
                subject = Subject.objects.get(id=subject_id)
            except Subject.DoesNotExist:
                pass
        
        # 문제집 생성
        topic_set = TopicQuestionSet.objects.create(
            title=title,
            description=description,
            subject=subject,
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


@login_required
@staff_member_required
def delete_topic_set(request, set_id):
    """주제별 문제집 삭제 (AJAX)"""
    from django.http import JsonResponse
    from exam.models import TopicQuestionSet
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'}, status=400)
    
    try:
        topic_set = TopicQuestionSet.objects.get(id=set_id)
        topic_set.delete()
        return JsonResponse({'success': True})
    except TopicQuestionSet.DoesNotExist:
        return JsonResponse({'success': False, 'error': '문제집을 찾을 수 없습니다.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ============================================================================
# 기본서 내용 생성 및 연습문제 자동 출제
# ============================================================================

@login_required
@staff_member_required
def textbook_generator(request):
    """기본서 내용 생성 및 연습문제 자동 출제 메인 페이지"""
    from practice.models import Book
    
    books = Book.objects.all().order_by('subject', 'name')
    
    return render(request, 'dashboard/textbook_generator.html', {
        'books': books,
        'page_title': '기본서 내용 생성',
    })


@login_required
@staff_member_required
def api_get_textbook_content(request):
    """목차에서 기본서 내용 가져오기 (AJAX)"""
    from django.http import JsonResponse
    from practice.models import Chapter
    from django.conf import settings
    import json
    
    # Imports for image generation
    try:
        import os
        import mimetypes
        import time
        from google import genai
        from google.genai import types
    except ImportError:
        pass
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'}, status=400)
    
    try:
        data = json.loads(request.body)
        chapter_id = data.get('chapter_id')
        
        if not chapter_id:
            return JsonResponse({'success': False, 'error': '목차를 선택해주세요.'})
        
        chapter = Chapter.objects.select_related('book').get(id=chapter_id)
        
        # 과목명 → 스토어 이름 매핑
        subject_name = chapter.book.subject
        store_name = subject_name  # 동일한 이름 사용
        
        # GeminiStoreManager로 내용 가져오기
        from fileSearchStore import GeminiStoreManager
        api_key = settings.GEMINI_API_KEY
        manager = GeminiStoreManager(api_key=api_key)
        manager.sync_all_stores()
        
        # 프롬프트 구성 (HTML 형식으로 요청)
        prompt = f'''{chapter.code}에 대해 HTML 형식으로 자세히 정리해줘.

[필수 규칙]
1. **제목 표시 금지**: 결과물의 맨 처음에 대목차 제목(예: {chapter.code} {chapter.title})을 작성하지 마시오. 바로 하위 내용부터 시작하시오.
2. 존대말 금지, "~함"체로 작성
3. 서적 페이지나 레퍼런스 언급 금지
4. **계층 구조 및 번호 매기기 규칙 (철저 준수)**:
   - 대분류: <div style="margin-left:0px; margin-top:20px; font-weight:bold; font-size:16px;"><span style="font-weight:bold; color:#2b6cb0; margin-right:4px;">(1)</span> 제목</div>
   - 중분류: <div style="margin-left:20px; margin-top:10px; font-weight:bold;"><span style="font-weight:bold; color:#2d3748; margin-right:4px;">가)</span> 내용</div>
   - 소분류: <div style="display:flex; align-items:flex-start; margin-left:40px; margin-top:5px;"><span style="flex-shrink:0; margin-right:4px;">1)</span><span>내용</span></div>
   - 예시:
     <div style="margin-left:0px; margin-top:20px; font-weight:bold; font-size:16px;"><span ...>(1)</span> 대제목</div>
     <div style="margin-left:20px; margin-top:10px; font-weight:bold;"><span ...>가)</span> 중제목 ...</div>
     <div style="display:flex; align-items:flex-start; margin-left:40px; margin-top:5px;"><span ...>1)</span><span>소내용 ...</span></div>
5. **HTML 스타일 및 간격 (여백 최소화)**:
   - 대제목: <h3 style="color:#2c5282; border-bottom:2px solid #4299e1; padding-bottom:2px; margin-top:20px; margin-bottom:4px; font-size:18px; letter-spacing:-0.5px;">제목</h3>
   - 소제목: <h4 style="color:#2d3748; margin-top:12px; margin-bottom:2px; font-size:16px; letter-spacing:-0.3px;">소제목</h4>
   - 키워드: <strong style="color:#c53030;">중요한 용어</strong>
   - 리스트 컨테이너: <div style="margin-left:8px; margin-top:0px; line-height:1.4;">
   - 박스: <div style="background:#ebf8ff; border-left:4px solid #3182ce; padding:8px 12px; margin:8px 0 8px 60px; border-radius:4px; font-size:14px; line-height:1.4;">
6. **LaTeX 및 영문 표기**:
   - 단순 영문 용어 및 단위(온도 등)는 LaTeX 쓰지 말고 일반 텍스트로 표기 (예: `(chitin)` O, `50°C` O)
   - LaTeX 사용 금지 예: `($\text{{chitin}}$)` X, `$50^\circ\text{{C}}$` X
   - 복잡한 화학식이나 수학 공식만 MathJax(LaTeX) 사용
7. 전체 내용을 <div style="font-family:'Google Sans Text', 'Google Sans', sans-serif; font-size:14px; line-height:1.5; color:#303030; letter-spacing:-0.2px;">로 감싸기
8. **제목 바로 아래 본문이 올 때 빈 줄 없이 바로 이어지도록 작성**
9. **줄간격 제약**: 문단 사이에도 빈 줄을 넣지 마십시오. 줄바꿈은 반드시 한 번만(`<br>`) 하십시오. (No double line breaks)
'''
        
        result = manager.query_store(store_name, prompt)
        
        return JsonResponse({
            'success': True,
            'content': result,
            'chapter_code': chapter.code,
            'chapter_title': chapter.title,
            'prompt': prompt,
        })
        
    except Chapter.DoesNotExist:
        return JsonResponse({'success': False, 'error': '목차를 찾을 수 없습니다.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@staff_member_required
def api_generate_quiz(request):
    """목차 기반 퀴즈 문제 생성 (AJAX)"""
    from django.http import JsonResponse
    from practice.models import Chapter
    from django.conf import settings
    import json
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'}, status=400)
    
    try:
        data = json.loads(request.body)
        chapter_id = data.get('chapter_id')
        
        if not chapter_id:
            return JsonResponse({'success': False, 'error': '목차를 선택해주세요.'})
        
        chapter = Chapter.objects.select_related('book').get(id=chapter_id)
        
        # 과목명 → 스토어 이름 매핑
        subject_name = chapter.book.subject
        store_name = subject_name
        
        # GeminiStoreManager로 퀴즈 생성
        from fileSearchStore import GeminiStoreManager
        api_key = settings.GEMINI_API_KEY
        manager = GeminiStoreManager(api_key=api_key)
        manager.sync_all_stores()
        
        # 프롬프트 구성
        prompt = f'''{chapter.code} {chapter.title}에 대한 내용 이해 문제를 5지선다형(문제번호\t문제\t보기1\t보기2\t보기3\t보기4\t보기5\t정답\t해설)으로 중복없이 최대한 출제하고 csv 형태로 만들어 주되 분리자는 tab으로 해'''
        
        result = manager.query_store(store_name, prompt)
        
        # TSV 파싱
        questions = []
        lines = result.strip().split('\n')
        for line in lines:
            if not line.strip():
                continue
            parts = line.split('\t')
            # 헤더 행 스킵
            if parts[0].strip() == '문제번호':
                continue
            if len(parts) >= 8:
                try:
                    q = {
                        'number': int(parts[0].strip()) if parts[0].strip().isdigit() else len(questions) + 1,
                        'content': parts[1].strip() if len(parts) > 1 else '',
                        'choice1': parts[2].strip() if len(parts) > 2 else '',
                        'choice2': parts[3].strip() if len(parts) > 3 else '',
                        'choice3': parts[4].strip() if len(parts) > 4 else '',
                        'choice4': parts[5].strip() if len(parts) > 5 else '',
                        'choice5': parts[6].strip() if len(parts) > 6 else '',
                        'answer': int(parts[7].strip()) if len(parts) > 7 and parts[7].strip().isdigit() else 1,
                        'explanation': parts[8].strip() if len(parts) > 8 else '',
                    }
                    questions.append(q)
                except (ValueError, IndexError):
                    continue
        
        return JsonResponse({
            'success': True,
            'questions': questions,
            'raw_tsv': result,
            'chapter_code': chapter.code,
            'chapter_title': chapter.title,
            'prompt': prompt,
        })
        
    except Chapter.DoesNotExist:
        return JsonResponse({'success': False, 'error': '목차를 찾을 수 없습니다.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@staff_member_required
def api_save_content(request):
    """생성된 내용 저장 (AJAX)"""
    from django.http import JsonResponse
    from practice.models import Chapter, ChapterContent
    import json
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'}, status=400)
    
    try:
        data = json.loads(request.body)
        chapter_id = data.get('chapter_id')
        content_text = data.get('content', '')
        
        if not chapter_id:
            return JsonResponse({'success': False, 'error': '목차를 선택해주세요.'})
        
        chapter = Chapter.objects.get(id=chapter_id)
        
        # 기존 콘텐츠가 있으면 업데이트, 없으면 생성
        content, created = ChapterContent.objects.update_or_create(
            chapter=chapter,
            defaults={
                'content': content_text,
                'author': request.user,
            }
        )
        
        return JsonResponse({
            'success': True,
            'created': created,
            'content_id': content.id,
        })
        
    except Chapter.DoesNotExist:
        return JsonResponse({'success': False, 'error': '목차를 찾을 수 없습니다.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def api_load_content(request):
    """지정된 목차의 저장된 내용 불러오기 (AJAX)"""
    from django.http import JsonResponse
    from practice.models import ChapterContent
    
    chapter_id = request.GET.get('chapter_id')
    if not chapter_id:
        return JsonResponse({'success': False, 'error': '목차를 선택해주세요.'})
        
    try:
        content_obj = ChapterContent.objects.get(chapter_id=chapter_id)
        return JsonResponse({
            'success': True,
            'content': content_obj.content,
            'updated_at': content_obj.updated_at.strftime('%Y-%m-%d %H:%M')
        })
    except ChapterContent.DoesNotExist:
        return JsonResponse({'success': True, 'content': '', 'message': '저장된 내용이 없습니다.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@staff_member_required
def api_save_quiz(request):
    """생성된 퀴즈 저장 (AJAX)"""
    from django.http import JsonResponse
    from practice.models import Chapter, PracticeQuestion
    import json
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'}, status=400)
    
    try:
        data = json.loads(request.body)
        chapter_id = data.get('chapter_id')
        questions = data.get('questions', [])
        
        if not chapter_id:
            return JsonResponse({'success': False, 'error': '목차를 선택해주세요.'})
        
        if not questions:
            return JsonResponse({'success': False, 'error': '저장할 문제가 없습니다.'})
        
        chapter = Chapter.objects.get(id=chapter_id)
        
        # 마지막 문제 번호 확인
        last_q = PracticeQuestion.objects.filter(chapter=chapter).order_by('-number').first()
        next_number = (last_q.number + 1) if last_q else 1
        
        created_count = 0
        for q in questions:
            PracticeQuestion.objects.create(
                chapter=chapter,
                number=next_number,
                content=q.get('content', ''),
                choice1=q.get('choice1', ''),
                choice2=q.get('choice2', ''),
                choice3=q.get('choice3', ''),
                choice4=q.get('choice4', ''),
                choice5=q.get('choice5', ''),
                answer=q.get('answer', 1),
                explanation=q.get('explanation', ''),
            )
            next_number += 1
            created_count += 1
        
        return JsonResponse({
            'success': True,
            'created_count': created_count,
        })
        
    except Chapter.DoesNotExist:
        return JsonResponse({'success': False, 'error': '목차를 찾을 수 없습니다.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@staff_member_required
def api_generate_textbook_image(request):
    """기본서 내용 기반 인포그래픽 이미지 생성 (AJAX)"""
    from django.http import JsonResponse
    from practice.models import Chapter
    from django.conf import settings
    import json
    import os
    import mimetypes
    import time
    from google import genai
    from google.genai import types

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'}, status=400)
    
    try:
        data = json.loads(request.body)
        chapter_id = data.get('chapter_id')
        context = data.get('context', '')[:1000]  # 너무 길면 자름
        
        if not chapter_id:
            return JsonResponse({'success': False, 'error': '목차를 선택해주세요.'})
            
        chapter = Chapter.objects.select_related('book').get(id=chapter_id)
        
        # 이미지 생성 프롬프트 구성
        prompt = f"""
Create a highly educational and visually appealing infographic for the following topic:
Topic: {chapter.title}

Key Concepts:
{context}

Requirements:
1. Visual Style: Cartoon and Watercolor style (artistic but accurate). High resolution.
2. Layout: Organized, easy to follow flow.
3. Content: Visualize the key concepts mentioned above (e.g., insect anatomy, lifecycle, classification).
4. Reference: If realistic details are required, reference real-world visual characteristics accurately but render them in the specified Cartoon/Watercolor style.
5. No text overload: Use icons, diagrams, and short labels rather than long text.
6. Language: Korean (if possible) or English labels.
"""
        
        # Gemini Client 설정
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        model = "gemini-3-pro-image-preview"
        
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                ],
            ),
        ]
        
        generate_content_config = types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="16:9", image_size="1K"),
        )
        
        # 이미지 생성 요청
        image_data = None
        mime_type = None
        
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if not chunk.candidates or not chunk.candidates[0].content.parts:
                continue
                
            part = chunk.candidates[0].content.parts[0]
            if part.inline_data and part.inline_data.data:
                image_data = part.inline_data.data
                mime_type = part.inline_data.mime_type
                break
        
        if not image_data:
            return JsonResponse({'success': False, 'error': '이미지 생성에 실패했습니다.'})
            
        # 임시 파일로 저장
        file_extension = mimetypes.guess_extension(mime_type) or ".png"
        timestamp = int(time.time())
        filename = f"textbook_{chapter.id}_{timestamp}{file_extension}"
        
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_infographics')
        os.makedirs(temp_dir, exist_ok=True)
        temp_filepath = os.path.join(temp_dir, filename)
        
        with open(temp_filepath, 'wb') as f:
            f.write(image_data)
            
        # URL 반환
        image_url = os.path.join(settings.MEDIA_URL, 'temp_infographics', filename).replace('\\', '/')
        
        return JsonResponse({
            'success': True,
            'image_url': image_url,
            'filename': filename
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@staff_member_required
def api_format_textbook_content(request):
    """기본서 내용 텍스트 포맷팅 (AJAX)"""
    from django.http import JsonResponse
    from practice.models import Chapter
    from django.conf import settings
    from fileSearchStore import GeminiStoreManager
    import json
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'}, status=400)
    
    try:
        data = json.loads(request.body)
        chapter_id = data.get('chapter_id')
        content = data.get('content', '')
        
        if not content.strip():
            return JsonResponse({'success': False, 'error': '포맷팅할 내용이 없습니다.'})
            
        chapter = None
        subject = "일반"
        chapter_info = ""
        
        if chapter_id:
            try:
                chapter = Chapter.objects.select_related('book').get(id=chapter_id)
                subject = chapter.book.subject
                chapter_info = f"{chapter.code} {chapter.title}"
            except Chapter.DoesNotExist:
                pass
        
        # Gemini Client 설정
        api_key = settings.GEMINI_API_KEY
        manager = GeminiStoreManager(api_key=api_key)
        # No need to sync stores for simple reformatting, but consistent with other views
        
        prompt = f"""
다음 텍스트를 [{subject}] 과목의 기본서 내용으로 정리해줘.
목차 정보: {chapter_info}

[원본 텍스트]
{content}

[요구사항]
1. 문체: 존대말을 쓰지 말고 "~함"으로 끝나는 개조식 문체를 사용해. (예: "특징은 다음과 같음.")
2. 포맷: 
   - 번호는 (1), (2), (3) 형식을 사용해.
   - 중요한 키워드는 **굵게** 표시해.
   - 머리기호(Bullet points)를 적절히 사용해.
3. 제외 사항:
   - 서적 페이지나 레퍼런스(참고문헌)에 대한 언급은 모두 제거해.
   - "이 텍스트는..." 같은 서론이나 결론 멘트 없이 내용만 출력해.
"""
        
        # Use generated content logic - query generic store or subject store if accessible
        # Since we are reformatting provided text, we don't necessarily need RAG, 
        # but using query_store is the standard way here. 
        # We can use the subject name as store_name to valid RAG if needed, 
        # or just "General"/system prompt if the class supports it.
        # Assuming query_store handles the prompt efficiently.
        
        formatted_content = manager.query_store(subject, prompt)
        
        return JsonResponse({
            'success': True,
            'content': formatted_content
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
