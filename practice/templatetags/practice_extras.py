from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """딕셔너리에서 키로 값을 가져오기"""
    if dictionary is None:
        return None
    return dictionary.get(key)


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
