from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Count
from .models import Subject, Term, TermReference


@login_required
def term_list(request):
    """용어 목록"""
    terms = Term.objects.prefetch_related('subjects', 'references').annotate(
        reference_count=Count('references')
    ).order_by('word')
    subjects = Subject.objects.all()
    
    # 과목 필터
    subject_id = request.GET.get('subject')
    if subject_id:
        terms = terms.filter(subjects__id=subject_id)
    
    # 검색
    search = request.GET.get('q')
    if search:
        terms = terms.filter(word__icontains=search)
    
    context = {
        'terms': terms,
        'subjects': subjects,
        'selected_subject': subject_id,
        'search_query': search or '',
    }
    return render(request, 'glossary/term_list.html', context)


@login_required
def term_detail(request, pk):
    """용어 상세 (ID로 조회)"""
    import markdown as md
    term = get_object_or_404(Term.objects.prefetch_related('subjects', 'references'), pk=pk)
    
    # 마크다운을 HTML로 렌더링 (extra, nl2br, sane_lists 확장 사용)
    rendered_content = md.markdown(
        term.content or '', 
        extensions=['extra', 'nl2br', 'sane_lists']
    )
    
    context = {
        'term': term,
        'rendered_content': rendered_content,
        'references': term.references.all(),
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
