from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
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
