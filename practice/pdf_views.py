from django.shortcuts import get_object_or_404, render
from .models import Chapter, ChapterContent, PracticeQuestion


def chapter_pdf(request, chapter_id):
    """챕터 내용과 연습문제를 인쇄용 페이지로 출력 (브라우저에서 PDF로 인쇄)"""
    chapter = get_object_or_404(Chapter, id=chapter_id)
    
    # 하위 챕터 모두 수집 (재귀적으로)
    def collect_descendants(parent):
        result = [parent]
        for child in parent.children.all().order_by('order', 'code'):
            result.extend(collect_descendants(child))
        return result
    
    all_chapters = collect_descendants(chapter)
    
    # 각 챕터의 컨텐츠와 문제 수집
    chapter_data = []
    for ch in all_chapters:
        content = getattr(ch, 'content', None)
        questions = ch.questions.all().order_by('number')
        chapter_data.append({
            'chapter': ch,
            'content': content,
            'questions': questions,
        })
    
    # 인쇄용 HTML 페이지 렌더링
    return render(request, 'practice/chapter_pdf.html', {
        'root_chapter': chapter,
        'chapter_data': chapter_data,
    })



