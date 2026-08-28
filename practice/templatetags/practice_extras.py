from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """딕셔너리에서 키로 값을 가져오기"""
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def topic_bold(value):
    """문제 미리보기에서 무엇을 묻는지(주제)를 굵게 만든다.

    '오리나무잎벌레의 피해에 대한 설명으로 옳은 것은?' 처럼
    앞쪽이 주제이고 뒤쪽은 '~옳은 것은?' 같은 상투적인 말이다.
    주제만 굵게 하면 목록에서 무엇을 묻는 문제인지 한눈에 들어온다.
    """
    import re
    from django.utils.html import escape
    from django.utils.safestring import mark_safe

    text = plain_text(value)
    if not text:
        return ''

    # 너무 길면 자른다 (자른 뒤에 굵게 해야 태그가 깨지지 않는다)
    if len(text) > 80:
        text = text[:80].rstrip() + '…'

    # 주제와 물음을 가르는 자리. 가장 앞에 나오는 것을 쓴다
    cuts = [
        '에 대한 설명', '에 관한 설명', '에 대한 내용', '에 관한 내용',
        '의 연결이', '의 연결로', '에 해당하는', '으로 옳', '로 옳',
        '으로 바르게', '로 바르게', '을 순서대로', '를 순서대로',
        '이 아닌 것', '가 아닌 것', '은 것은?', '는 것은?',
    ]
    best = None
    for pat in cuts:
        i = text.find(pat)
        if i > 1 and (best is None or i < best):
            best = i
    head, tail = (text[:best], text[best:]) if best else (text, '')

    return mark_safe('<b>%s</b>%s' % (escape(head), escape(tail)))


@register.filter
def plain_text(value):
    """미리보기용으로 태그를 걷어내고 &lt; 같은 엔티티도 글자로 되돌린다.

    문제 본문에 '&lt;보기&gt;' 가 엔티티로 저장된 것이 있다.
    striptags 만 쓰면 엔티티가 그대로 남아 화면에 '&lt;보기&gt;' 로 보인다.
    """
    import html
    import re

    if not value:
        return ''
    text = str(value)
    # <보기> 처럼 한글이 든 꺾쇠는 태그가 아니라 글이다. 먼저 지켜 둔다
    text = re.sub(r'<([^<>]*[가-힣][^<>]*)>', r'〈\1〉', text)
    # <br>, </div> 등이 붙은 자리는 띄어 준다 (글자가 서로 붙지 않게)
    text = re.sub(r'<(br|/p|/div|/li|/tr)[^>]*>', ' ', text, flags=re.I)
    text = re.sub(r'<[^>]+>', '', text)      # 남은 태그 제거
    text = html.unescape(text)               # &lt; -> <, &nbsp; -> 공백
    # 엔티티가 풀리며 다시 생긴 꺾쇠도 홑화살괄호로
    text = text.replace('<', '〈').replace('>', '〉')
    return re.sub(r'\s+', ' ', text).strip()




@register.filter
def make_list_with(value, arg):
    """두 값을 리스트로 만들기"""
    return [value, arg]


@register.filter
def add_to_list(lst, value):
    """리스트에 값 추가"""
    if isinstance(lst, list):
        return lst + [value]
    return [lst, value]


@register.filter
def has_content(chapter):
    """목차에 학습 컨텐츠가 있는지 확인"""
    try:
        return chapter.content is not None
    except:
        return False


@register.filter
def clean_math(value):
    """선지·문제에 든 $...$ 표기를 정리한다.

    학명이 $Adoretus tenuimaculatus$ 로 저장된 것이 있다. 그대로 두면
    MathJax 가 수식으로 그려 세리프체가 되고 낱말 사이 공백까지 사라진다.
    학명은 <i> 로, 그 밖의 영문은 보통 글자로 바꾸고
    진짜 수식($CO_2$ 등)은 건드리지 않는다.
    """
    from django.utils.safestring import mark_safe

    if not value:
        return ''

    try:
        from glossary.views import _unwrap_plain_math
    except Exception:
        return mark_safe(str(value))

    return mark_safe(_unwrap_plain_math(str(value)))


@register.filter
def inline_explanation(value):
    """정답 선지 밑에 붙일 해설.

    주제별 문제 화면(topic_solve)처럼 형광 띠를 긋는다. 다만 연습문제 해설은
    두 갈래다.

      - 한 문단짜리 짧은 해설 (400개): 통째로 형광을 그어도 된다
      - 여러 문단에 '[선지별 답변]'까지 든 긴 해설 (1,059개):
        통째로 그으면 화면 한 장이 노랗게 되고, 마크다운이 내놓는
        <p> 조각을 인라인 span 안에 넣게 되어 태그도 어긋난다

    그래서 <p>나 목록으로 쪼개지지 않은 것만 형광을 두른다.
    """
    from django.utils.safestring import mark_safe

    from exam.templatetags.markdown_extras import markdown_format as md

    if not value:
        return ""

    html = str(md(value)).strip()

    # 블록으로 쪼개졌으면 형광을 두르지 않는다 (태그가 어긋난다)
    lowered = html.lower()
    if any(t in lowered for t in ("<p", "</p", "<ul", "<ol", "<li", "<h1", "<h2",
                                  "<h3", "<h4", "<blockquote", "<table", "<br")):
        return mark_safe(html)

    return mark_safe('<span class="hl">' + html + "</span>")
