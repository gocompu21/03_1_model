from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .models import Subject, Term, TermReference


@login_required
def term_list(request):
    """용어 목록"""
    terms = Term.objects.prefetch_related('subjects').all()
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
    term = get_object_or_404(Term.objects.prefetch_related('subjects', 'references'), pk=pk)
    
    context = {
        'term': term,
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
    
    context = {
        'term': term,
        'subjects': subjects,
        'edit_mode': True,
    }
    return render(request, 'glossary/term_form.html', context)

