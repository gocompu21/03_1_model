import re
from django import template
from django.utils.safestring import mark_safe
from glossary.models import Term, TermReference

register = template.Library()


@register.filter(name='link_terms')
def link_terms(content, source_info=None):
    """
    [[용어]] 형식을 glossary 링크로 변환
    
    Usage in template:
        {{ content|link_terms }}
        {{ content|link_terms:"chapter_content:123" }}
    
    Args:
        content: HTML 컨텐츠
        source_info: "source_type:source_id" 형식 (역참조 등록용, 선택)
    """
    if not content:
        return content
    
    # [[용어]] 패턴 찾기
    pattern = r'\[\[([^\]]+)\]\]'
    
    def replace_term(match):
        term_word = match.group(1).strip()
        
        try:
            term = Term.objects.get(word=term_word)
            
            # 역참조 등록 (source_info가 제공된 경우)
            if source_info:
                try:
                    source_type, source_id = source_info.split(':')
                    TermReference.objects.get_or_create(
                        term=term,
                        source_type=source_type,
                        source_id=int(source_id),
                        defaults={'source_title': f'{source_type} #{source_id}'}
                    )
                except (ValueError, Exception):
                    pass
            
            # 링크로 변환
            return f'<a href="/glossary/term/{term.pk}/" class="glossary-link" title="용어: {term_word}">{term_word}</a>'
        
        except Term.DoesNotExist:
            # 용어가 없으면 원본 텍스트 반환 (대괄호 없이)
            return f'<span class="glossary-missing" title="미등록 용어">{term_word}</span>'
    
    result = re.sub(pattern, replace_term, content)
    return mark_safe(result)


@register.simple_tag
def glossary_styles():
    """Glossary 링크 스타일 CSS 반환"""
    return mark_safe('''
    <style>
        .glossary-link {
            color: #2d6a4f;
            text-decoration: underline;
            text-decoration-style: dotted;
            cursor: pointer;
        }
        .glossary-link:hover {
            background: #e8f5e9;
            text-decoration-style: solid;
        }
        .glossary-missing {
            color: #999;
            border-bottom: 1px dashed #ccc;
        }
    </style>
    ''')
