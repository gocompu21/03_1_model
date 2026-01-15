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


from glossary.utils import get_terms_pattern


@register.filter(name='autolink_terms')
def autolink_terms(content, subject_name=None):
    """
    텍스트 내의 용어를 자동으로 링크로 변환 (과목 기준)
    
    Usage:
        {{ text|autolink_terms:"수목병리학" }}
    """
    if not content or not subject_name:
        return content
        
    pattern, term_map = get_terms_pattern(subject_name)
    if not pattern:
        return content
        
    def replace_func(match):
        word = match.group(0)
        term_id = term_map.get(word)
        if term_id:
            # target="glossary_popup"으로 설정하여 하나의 창만 재사용
            return f'<a href="/glossary/term/{term_id}/" class="glossary-link" target="glossary_popup" title="용어: {word}">{word}</a>'
        return word
        
    # 이미 링크된 태그 내부나 HTML 속성 등을 제외하고 텍스트만 치환하도록 복잡하게 짜는 대신,
    # 여기서는 마크다운 변환 전의 Plain Text라고 가정하고 단순 치환.
    # 만약 HTML이 섞여있다면 BeautifulSoup 등을 써야 하지만 성능 이슈가 있음.
    # 현재는 Markdown 필터 적용 전에 이 필터를 적용할 것이므로 텍스트 상태임.
    
    return mark_safe(pattern.sub(replace_func, content))


@register.simple_tag
def get_relevant_terms(content, subject_name=None):
    """
    텍스트에 포함된 용어 목록을 반환 (중복 제거)
    
    Usage:
        {% get_relevant_terms content.content chapter.book.subject as terms %}
        {% get_relevant_terms question_object subject_object as terms %}
    """
    if not content or not subject_name:
        return []

    # Handle Subject object (if passed instead of string name)
    if hasattr(subject_name, 'name'):
        subject_name = subject_name.name
    
    # Handle content being an object (Question model)
    search_text = ""
    if isinstance(content, str):
        search_text = content
    else:
        # Check for Question-like object (with choices)
        # exam.models.Question or practice.models.PracticeQuestion
        if hasattr(content, 'content'):
            search_text += content.content + " "
        
        for i in range(1, 6):
            choice_field = f'choice{i}'
            if hasattr(content, choice_field):
                search_text += getattr(content, choice_field) + " "
        
        # Optionally include explanation if available
        if hasattr(content, 'general_chat') and content.general_chat:
            search_text += content.general_chat + " "
        if hasattr(content, 'textbook_chat') and content.textbook_chat:
            search_text += content.textbook_chat + " "
        if hasattr(content, 'explanation') and content.explanation:  # PracticeQuestion
            search_text += content.explanation + " "

    if not search_text:
        return []
        
    pattern, term_map = get_terms_pattern(subject_name)
    if not pattern:
        return []
        
    found_term_ids = set()
    
    # 텍스트에서 모든 매칭 찾기
    for match in pattern.finditer(search_text):
        term_id = term_map.get(match.group(0))
        if term_id:
            found_term_ids.add(term_id)
            
    if not found_term_ids:
        return []
        
    # 용어 객체 조회 (정렬)
    from glossary.models import Term
    from django.db.models import Count
    return Term.objects.filter(id__in=found_term_ids).annotate(
        reference_count=Count('references')
    ).order_by('word')


@register.filter(name='get_initial')
def get_initial(value):
    """
    한글 문자열의 초성을 반환합니다. 영문/숫자는 그대로 또는 대문자화.
    사용자 요청 그룹: 1, A, S, 가, 나, 다, 라, 마, 바, 사, 아, 자, 차, 카, 타, 파, 하
    """
    if not value:
        return ''
        
    char = value[0]
    
    # 1. 숫자
    if char.isdigit():
        return '1'
        
    # 2. 한글
    if '가' <= char <= '힣':
        # 초성 인덱스 계산
        initial_index = (ord(char) - 0xAC00) // 588
        
        # 초성 리스트 (19개)
        # ㄱ ㄲ ㄴ ㄷ ㄸ ㄹ ㅁ ㅂ ㅃ ㅅ ㅆ ㅇ ㅈ ㅉ ㅊ ㅋ ㅌ ㅍ ㅎ
        initials = ['가', '가', '나', '다', '다', '라', '마', '바', '바', '사', '사', '아', 
                    '자', '자', '차', '카', '타', '파', '하']
                    
        if 0 <= initial_index < len(initials):
            return initials[initial_index]
            
    # 3. 영문
    if 'a' <= char <= 'z':
        if char <= 'n': return 'a~n'
        return 'o~z'
    elif 'A' <= char <= 'Z':
        if char <= 'N': return 'A~N'
        return 'O~Z'
        
    return char


def is_hangul(value):
    """문자열이 한글로 시작하는지 여부 반환"""
    if not value:
        return False
    return '가' <= value[0] <= '힣'


@register.filter
def summarize_question(content):
    """
    문제 내용을 간단한 주제로 요약합니다.
    예: "파이토플라스마의 설명 중 옳지 않은 것은?" -> "파이토플라스마 설명"
    """
    if not content:
        return ""
    
    text = content.strip()
    
    # HTML 태그 제거
    text = re.sub(r'<[^>]+>', '', text)
    
    # 줄바꿈을 공백으로
    text = re.sub(r'\s+', ' ', text)
    
    # 불필요한 문구 제거 패턴 (순서 중요: 긴 패턴 먼저)
    remove_patterns = [
        # 설명 관련
        r'에 대한 설명으로 옳은 것은\?*',
        r'에 대한 설명으로 옳지 않은 것은\?*',
        r'에 대한 설명 중 옳은 것은\?*',
        r'에 대한 설명 중 옳지 않은 것은\?*',
        r'의 설명으로 옳은 것은\?*',
        r'의 설명으로 옳지 않은 것은\?*',
        r'의 설명 중 옳은 것은\?*',
        r'의 설명 중 옳지 않은 것은\?*',
        r'에 관한 설명으로 옳은 것은\?*',
        r'에 관한 설명으로 옳지 않은 것은\?*',
        # 일반적인 질문 패턴
        r'으로 옳은 것은\?*',
        r'으로 옳지 않은 것은\?*',
        r'로 옳은 것은\?*',
        r'로 옳지 않은 것은\?*',
        r'중 옳은 것은\?*',
        r'중 옳지 않은 것은\?*',
        # 긴 패턴 (문장 중간~끝까지 제거)
        r'을 할 수 있는 것은\?*',
        r'를 할 수 있는 것은\?*',
        r'할 수 있는 것은\?*',
        r'이지만[^?]*것은\?*',
        r'지만[^?]*것은\?*',
        r',\s*조건에 따라서는[^?]*',
        # 끝에 오는 패턴들
        r'것은\?*$',
        r'무엇인가\?*$',
        r'무엇인가요\?*$',
        # 시작 부분 제거
        r'^다음 중 ',
        r'^다음의 ',
        r'^아래 중 ',
        r'\?$',
    ]
    
    # 패턴 제거
    for pattern in remove_patterns:
        text = re.sub(pattern, '', text)
    
    text = text.strip()
    
    # 쉼표가 있으면 첫 부분만
    if ',' in text:
        text = text[:text.find(',')]
    
    # 최대 15자
    text = text.strip()
    if len(text) > 15:
        text = text[:15]
    
    # 마지막 조사/접속어 정리
    text = re.sub(r'(은|는|이|가|을|를|의|에|며|고|하며|이며|으며|하는|하고)$', '', text.strip())
    
    return text.strip()

