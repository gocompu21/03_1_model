from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Count
from .models import Subject, Term, TermReference


@login_required
def term_list(request):
    """용어 목록"""
    from glossary.templatetags.glossary_tags import get_initial
    
    # 1. 쿼리셋 기본 준비 (Prefetch 필수)
    terms_qs = Term.objects.prefetch_related('subjects', 'references').order_by('word')
    subjects = Subject.objects.all()
    
    # 과목 필터 (기본값: 수목해충학)
    subject_id = request.GET.get('subject')
    if subject_id is None:
        default_subject = Subject.objects.filter(name__contains='수목해충학').first()
        if default_subject:
            subject_id = str(default_subject.id)
    
    # 과목 필터링 (DB 레벨)
    if subject_id:
        terms_qs = terms_qs.filter(subjects__id=subject_id)
    
    # 검색 (DB 레벨)
    search = request.GET.get('q')
    if search:
        terms_qs = terms_qs.filter(word__icontains=search)

    # 기출 필터 설정
    exam_only = request.GET.get('exam_only', 'on')
    # off가 아니면 on으로 취급
    is_exam_only = (exam_only != 'off')
    if not is_exam_only: 
        exam_only = 'off'
    else:
        exam_only = 'on'

    # 과목별 문제 ID 캐싱 (필터링용)
    valid_question_ids = None
    if subject_id and subject_id.isdigit():
        try:
            from exam.models import Question
            # 해당 과목의 모든 문제 ID 가져오기
            valid_question_ids = set(Question.objects.filter(subject_id=int(subject_id)).values_list('id', flat=True))
        except ImportError:
            pass

    # 2. Python 레벨 처리 (Reference 필터링 및 리스트 변환)
    final_terms = []
    
    # QuerySet 실행
    for term in terms_qs:
        all_refs = list(term.references.all())
        filtered_refs = []
        
        if valid_question_ids is not None:
            for ref in all_refs:
                if ref.source_type == 'question':
                    # 해당 과목의 문제인 경우만 포함
                    if ref.source_id in valid_question_ids:
                        filtered_refs.append(ref)
                else:
                    # 챕터 등 다른 참조는 포함
                    filtered_refs.append(ref)
        else:
            # 전체 보기 모드: 모든 참조 포함
            filtered_refs = all_refs
            
        # 템플릿에서 사용할 속성 설정
        term.filtered_references = filtered_refs
        term.filtered_ref_count = len(filtered_refs)
        
        # 기출문제가 있는 것만 보기 필터
        if is_exam_only:
            if term.filtered_ref_count > 0:
                final_terms.append(term)
        else:
            final_terms.append(term)
    
    # 정렬: 초성 기준 (Python Sort)
    final_terms.sort(key=lambda t: (get_initial(t.word), t.word))

    context = {
        'terms': final_terms,
        'subjects': subjects,
        'selected_subject': subject_id,
        'search_query': search or '',
        'exam_only': is_exam_only,
    }
    return render(request, 'glossary/term_list.html', context)


@login_required
def term_detail(request, pk):
    """용어 상세 (ID로 조회)"""
    import markdown as md
    import re
    term = get_object_or_404(Term.objects.prefetch_related('subjects', 'references'), pk=pk)
    
    content = term.content or ''
    
    # LaTeX 수식을 임시로 보호 (마크다운 변환에서 제외)
    latex_formulas = []
    def save_latex(match):
        latex_formulas.append(match.group(0))
        return f'LATEXPLACEHOLDER{len(latex_formulas)-1}ENDLATEX'
    
    # $...$ 또는 $$...$$ 패턴 보호
    content = re.sub(r'\$\$[^$]+\$\$|\$[^$]+\$', save_latex, content)
    
    # 마크다운을 HTML로 렌더링 (extra, nl2br, sane_lists 확장 사용)
    rendered_content = md.markdown(
        content, 
        extensions=['extra', 'nl2br', 'sane_lists']
    )
    
    # LaTeX 수식 복원
    # LaTeX 수식 복원
    for i, formula in enumerate(latex_formulas):
        rendered_content = rendered_content.replace(f'LATEXPLACEHOLDER{i}ENDLATEX', formula)
    
    # 과목 필터링 (기출문제 연결 시 타 과목 문제 제외)
    subject_id = request.GET.get('subject')
    references = list(term.references.all())
    
    if subject_id and subject_id.isdigit():
        # 해당 과목 ID로 필터링
        target_subject_id = int(subject_id)
        
        # Exam 앱의 Question 모델 임포트 (Circular Import 방지 위해 함수 내부 임포트)
        try:
            from exam.models import Question
            
            # Question 타입 참조만 필터링
            question_refs = [r for r in references if r.source_type == 'question']
            if question_refs:
                question_ids = [r.source_id for r in question_refs]
                
                # 해당 과목의 문제 ID 조회
                valid_ids = set(Question.objects.filter(
                    id__in=question_ids, 
                    subject_id=target_subject_id
                ).values_list('id', flat=True))
                
                # 필터링: (질문이 아니거나) OR (질문이면서 유효한 과목인 경우)
                references = [
                    r for r in references 
                    if r.source_type != 'question' or r.source_id in valid_ids
                ]
        except ImportError:
            # exam 앱을 찾을 수 없는 경우 등 예외 처리 (조용히 무시하지 않고 로깅하면 좋겠지만)
            pass 
            
    context = {
        'term': term,
        'rendered_content': rendered_content,
        'references': references,
    }
    return render(request, 'glossary/term_detail.html', context)


@login_required
def term_by_word(request, word):
    """용어 상세 (용어명으로 조회)"""
    term = get_object_or_404(Term.objects.prefetch_related('subjects', 'references'), word=word)
    
    context = {
        'term': term,
        'references': term.references.all(),
    }
    return render(request, 'glossary/term_detail.html', context)


@login_required
def subject_terms(request, pk):
    """과목별 용어 목록"""
    subject = get_object_or_404(Subject, pk=pk)
    terms = subject.terms.all()
    
    context = {
        'subject': subject,
        'terms': terms,
    }
    return render(request, 'glossary/subject_terms.html', context)


@login_required
@staff_member_required
def term_delete(request, pk):
    """용어 삭제"""
    term = get_object_or_404(Term, pk=pk)
    
    if request.method == 'POST':
        word = term.word
        term.delete()
        messages.success(request, f'"{word}" 용어가 삭제되었습니다.')
        return redirect('glossary:term_list')
    
    return redirect('glossary:term_detail', pk=pk)


@login_required
@staff_member_required
def term_create(request):
    """용어 등록"""
    subjects = Subject.objects.all()
    
    if request.method == 'POST':
        word = request.POST.get('word', '').strip()
        content = request.POST.get('content', '').strip()
        subject_ids = request.POST.getlist('subjects')
        
        if not word:
            messages.error(request, '용어를 입력해주세요.')
        elif Term.objects.filter(word=word).exists():
            messages.error(request, f'"{word}" 용어가 이미 존재합니다.')
        else:
            term = Term.objects.create(word=word, content=content)
            if subject_ids:
                term.subjects.set(subject_ids)
            messages.success(request, f'"{word}" 용어가 등록되었습니다.')
            return redirect('glossary:term_detail', pk=term.pk)
    
    context = {
        'subjects': subjects,
    }
    return render(request, 'glossary/term_form.html', context)


@login_required
@staff_member_required
def term_edit(request, pk):
    """용어 수정"""
    term = get_object_or_404(Term, pk=pk)
    subjects = Subject.objects.all()
    
    if request.method == 'POST':
        word = request.POST.get('word', '').strip()
        content = request.POST.get('content', '').strip()
        subject_ids = request.POST.getlist('subjects')
        
        if not word:
            messages.error(request, '용어를 입력해주세요.')
        elif Term.objects.filter(word=word).exclude(pk=pk).exists():
            messages.error(request, f'"{word}" 용어가 이미 존재합니다.')
        else:
            term.word = word
            term.content = content
            term.save()
            term.subjects.set(subject_ids)
            messages.success(request, f'"{word}" 용어가 수정되었습니다.')
            return redirect('glossary:term_detail', pk=term.pk)
    
    # 마크다운을 HTML로 변환해서 Quill 에디터에 전달
    import markdown as md
    rendered_content = md.markdown(term.content or '', extensions=['extra', 'nl2br', 'sane_lists'])
    
    context = {
        'term': term,
        'rendered_content': rendered_content,
        'subjects': subjects,
        'edit_mode': True,
    }
    return render(request, 'glossary/term_form.html', context)


@login_required
@staff_member_required
def api_add_term(request):
    """API: 용어 추가 (JSON 응답)"""
    from django.http import JsonResponse
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST 요청만 허용됩니다.'}, status=405)
    
    word = request.POST.get('word', '').strip()
    content = request.POST.get('content', '').strip()
    subject_id = request.POST.get('subject_id', '')
    
    if not word:
        return JsonResponse({'success': False, 'error': '용어를 입력해주세요.'})
    
    # Check if term already exists
    if Term.objects.filter(word=word).exists():
        return JsonResponse({'success': False, 'error': f'"{word}" 용어가 이미 존재합니다.'})
    
    try:
        term = Term.objects.create(word=word, content=content)
        if subject_id:
            term.subjects.set([subject_id])
        return JsonResponse({'success': True, 'term_id': term.pk, 'word': word})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@staff_member_required
def api_upload_image(request):
    """이미지 업로드 API for Quill editor"""
    from django.http import JsonResponse
    from django.conf import settings
    import os
    import uuid
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    if 'image' not in request.FILES:
        return JsonResponse({'error': 'No image provided'}, status=400)
    
    image = request.FILES['image']
    
    # Generate unique filename
    ext = os.path.splitext(image.name)[1].lower()
    if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
        return JsonResponse({'error': 'Invalid image format'}, status=400)
    
    filename = f"{uuid.uuid4().hex}{ext}"
    
    # Save to media/term_images/
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'term_images')
    os.makedirs(upload_dir, exist_ok=True)
    
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, 'wb+') as f:
        for chunk in image.chunks():
            f.write(chunk)
    
    # Return URL
    image_url = f"{settings.MEDIA_URL}term_images/{filename}"
    return JsonResponse({'success': True, 'url': image_url})


@login_required
@staff_member_required
def fetch_term_from_textbook(request, pk):
    """기본서에서 용어 검색 및 설명 가져오기 (Gemini API 사용)"""
    import sys
    import os
    from django.conf import settings
    
    # Ensure project root is in path to import fileSearchStore
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    try:
        from fileSearchStore import GeminiStoreManager
    except ImportError:
        messages.error(request, 'fileSearchStore 모듈을 찾을 수 없습니다.')
        return redirect('glossary:term_detail', pk=pk)

    term = get_object_or_404(Term, pk=pk)
    
    if request.method == 'POST':
        try:
            # 1. 대상 과목(Store) 결정
            # 용어에 연결된 첫 번째 과목을 기준으로 함. 없으면 'Tree Doctor Examp'(전체)
            target_store = "Tree Doctor Examp"
            subject = term.subjects.first()
            if subject:
                # Store Map: 과목명 -> 스토어명 매핑 (notebook/views.py 참고할 수도 있으나, 
                # 현재 시스템은 과목명이 그대로 스토어명으로 사용되는 것으로 추정됨)
                target_store = subject.name
            
            # 2. 질문 생성
            user_input = f"'{term.word}'에 대해 설명해줘."
            
            # 3. API 호출
            api_key = settings.GEMINI_API_KEY
            manager = GeminiStoreManager(api_key=api_key)
            
            # 스토어 확인 및 싱크
            if target_store not in manager.stores or not manager.stores[target_store]:
                 manager.sync_all_stores()
            
            # 쿼리 실행
            response_text = manager.query_store(target_store, user_input)
            
            # 결과 검증 (빈 응답 등)
            if "No valid (ACTIVE) files found" in response_text or "Store is empty" in response_text:
                 manager.sync_all_stores()
                 response_text = manager.query_store(target_store, user_input)

            # 4. 결과 저장
            if response_text:
                # 기존 내용이 있으면 아래에 추가
                if term.content:
                    term.content += f"\n\n---\n###기본서 발췌 ({target_store})\n{response_text}"
                else:
                    term.content = response_text
                
                term.save()
                messages.success(request, f'기본서({target_store})에서 내용을 가져왔습니다.')
            else:
                messages.warning(request, 'API로부터 응답을 받지 못했습니다.')
                
        except Exception as e:
            messages.error(request, f'오류가 발생했습니다: {str(e)}')
            
    return redirect('glossary:term_detail', pk=pk)
