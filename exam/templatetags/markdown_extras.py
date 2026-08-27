from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape
import markdown as md
import re

from functools import lru_cache

register = template.Library()

# 마크다운 표 한 덩어리: 머리줄 + 구분선(|---|---|) + 본문 줄들.
# 마지막 줄은 </li> 처럼 닫는 태그가 뒤에 붙어 있을 수 있다.
TABLE_BLOCK_RE = re.compile(
    r"(?m)^[ \t]*(\|[^\n]*\|)[ \t]*\n"          # 머리줄
    r"[ \t]*\|[\s:-]+\|[ \t]*\n"                 # 구분선
    r"((?:[ \t]*\|[^\n]*\|[ \t]*(?:\n|$))+)"     # 본문 줄 (1줄 이상)
)

# 표 본문 줄 끝에 닫는 HTML 태그가 붙은 경우를 떼어내기 위한 패턴
TRAILING_TAGS_RE = re.compile(r"((?:</\w+>\s*)+)$")


def _render_tables_in_html_blocks(text):
    """HTML 블록(<li>, <td> 등) 안에 있는 마크다운 표를 직접 HTML로 바꾼다.

    Python-Markdown은 HTML 블록 내부를 마크다운으로 해석하지 않아
    표가 파이프 문자 그대로 남는다. 표 덩어리만 찾아 미리 변환한다.
    """

    def to_html(match):
        header = [c.strip() for c in match.group(1).strip().strip("|").split("|")]

        rows, tail = [], ""
        for line in match.group(2).strip().split("\n"):
            line = line.strip()
            # 마지막 줄 끝의 </li> 같은 닫는 태그는 표 밖으로 되돌린다
            closing = TRAILING_TAGS_RE.search(line)
            if closing:
                tail = closing.group(1).strip()
                line = line[: closing.start()].rstrip()
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if any(cells):
                rows.append(cells)

        head = "".join(f"<th>{c}</th>" for c in header)
        body = "".join(
            "<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows
        )
        return f"\n<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>\n{tail}"

    return TABLE_BLOCK_RE.sub(to_html, text)


@register.filter(name="markdown")
@lru_cache(maxsize=512)
def markdown_format(text):
    if not text:
        return ""
    # Pre-process to protect common LaTeX/MathJax commands from Markdown escaping
    # Markdown consumes one backslash, so we need double for it to survive into HTML for MathJax.
    # Pre-process to protect common LaTeX/MathJax commands from Markdown escaping
    # Markdown consumes one backslash, so we need double for it to survive into HTML for MathJax.
    if text:
        # 1. Remove <p> tags wrapping markdown tables so they can be parsed as blocks
        text = re.sub(r'<p>\s*(\|[\s\S]*?\|)\s*</p>', r'\n\1\n', text)

        # 2. Fix broken tables where formatting is merged into one line " | | "
        text = re.sub(r'\|\s+(?=\|)', '|\n', text)

        # 3. 표가 앞 문장 끝에 붙어 있으면 줄을 나눈다.
        #    AI 답변이 "...약제 농도| 구분 | 단위 |" 처럼 이어붙는 경우가 잦다.
        #    다음 줄이 구분선(|---|---|)인 파이프 줄을 표 머리로 보고 앞을 끊는다.
        text = re.sub(
            r'(?m)^(?P<head>.*?\S)(?P<row>\|[^\n]*\|)\s*$(?=\n[ \t]*\|[\s:-]+\|)',
            lambda m: f"{m.group('head')}\n\n{m.group('row')}",
            text,
        )

        # 3.1. <li>/<td> 등 HTML 블록 안의 표는 Python-Markdown이 건너뛴다.
        #      표 부분만 떼어 따로 변환한 뒤 다시 끼워 넣는다.
        text = _render_tables_in_html_blocks(text)

        # 4. Manually process bold text (**...**) to handle cases inside HTML blocks (div/span)
        #    Python-Markdown ignores markdown inside HTML blocks by default.
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)

        # 4.1. Manually process italic text (*...*) for scientific names etc.
        #      Must be after bold processing to avoid conflicts
        #      Strict: content must start/end with non-space, max 50 chars
        text = re.sub(r'\*(\S[^\*\n]{0,48}?\S|\S)\*', r'<em>\1</em>', text)

        # 4.5. Convert $\text{...}$ to plain text (avoid MathJax rendering issues)
        #      \text{} is just for displaying text, no math formatting needed
        text = re.sub(r'\$\\text\{([^}]+)\}\$', r'\1', text)

        # 5. Remove list markers (*, -) at the start of lines (handling leading whitespace)
        #    Fixes issue where asterisks appear in text when markdown list parsing fails (e.g. no blank line)
        #    or simply forces the "no bullet" style by flattening lists to text.
        text = re.sub(r'(?m)^\s*[\*\-]\s+', '', text)

        # 5.5. 연속 텍스트 들여쓰기: 6칸 이상 들여쓴 줄은 상위 마커(가, 나 등)의
        #      본문이므로 indent div로 감싸서 들여쓰기 유지
        text = re.sub(r'(?m)^[ \t]{6,}(\S.+)$', r'<div class="indent-cont">\1</div>', text)

        # 5.6. Remove leading 4-space indentation that causes code block rendering
        #      This prevents explanation text from being wrapped in <pre><code> tags
        #      which breaks MathJax rendering
        text = re.sub(r'(?m)^    ', '', text)

        # 6. Wrap lines starting with circled numbers (①-⑳) in a div with hanging-indent class.
        #    This ensures that multi-line text aligns correctly (hanging indent).
        #    Unicode range: \u2460 (①) to \u2473 (⑳)
        #    We match optional leading whitespace (^\s*) but do not capture it, effectively stripping it.
        #    ALSO: We must handle cases where the number is bolded (**①**) which becomes <strong>①...
        #    So we match optional <strong> tag at the start of the line.
        text = re.sub(r'(?m)^\s*((?:<strong>\s*)?[\u2460-\u2473].*)$', r'<div class="hanging-indent">\1</div>', text)

        # 7. 숫자)가 단독 줄에 있고 다음 줄에 텍스트가 있는 경우 한 줄로 병합
        #    예: "1)\n등판(tergum)..." → "1) 등판(tergum)..."
        text = re.sub(r'(?m)^\s*(\d+\))\s*\n\s*(\S)', r'\1 \2', text)

        # 8. (숫자), 가)~하), 숫자) 패턴에 hanging-indent 적용
        #    (1) 복부의 기본 구조... → <div class="hi-paren">(1) 복부의...</div>
        text = re.sub(r'(?m)^\s*(\(\d+\)\s+.+)$', r'<div class="hi-paren">\1</div>', text)
        #    가) 복부 경판의 특징... → <div class="hi-kr">가) 복부 경판의...</div>
        text = re.sub(r'(?m)^\s*([가-하]\)\s+.+)$', r'<div class="hi-kr">\1</div>', text)
        #    1) 등판(tergum)과... → <div class="hi-num">1) 등판(tergum)과...</div>
        text = re.sub(r'(?m)^\s*(\d+\)\s+.+)$', r'<div class="hi-num">\1</div>', text)

    # Convert markdown to HTML
    html = md.markdown(text, extensions=["extra", "nl2br"])
    # If it's a single paragraph, strip the <p> tags to avoid unwanted margins if user requests
    # But usually we want proper HTML.
    # User specifically asked to REMOVE <p> tags from the question content.
    # So we will strip wrapping <p> if it exists.
    if html.startswith("<p>") and html.endswith("</p>"):
        html = html[3:-4]
    return mark_safe(html)


@register.filter(name="circle_number")
def circle_number(value):
    try:
        value = int(value)
        if 1 <= value <= 20:
            return chr(0x245F + value)
        elif 21 <= value <= 35:
            return chr(0x3250 + value)
        elif 36 <= value <= 50:
            return chr(0x32B0 + value)
        else:
            return str(value)
    except (ValueError, TypeError):
        return value


import html as html_lib


@register.filter(name="format_question")
def format_question(text):
    if not text:
        return ""

    # Unescape first to handle &lt;p&gt;
    text = html_lib.unescape(text)

    # Helper to strip p tags (escaped and unescaped, case insensitive)
    def strip_p_tags(s):
        # Remove &lt;p&gt;, &lt;p ...&gt;, &lt;/p&gt; (in case unescape didn't catch weird ones)
        s = re.sub(r"&lt;p\b.*?&gt;", "", s, flags=re.IGNORECASE)
        s = re.sub(r"&lt;/p&gt;", "", s, flags=re.IGNORECASE)
        # Remove <p>, <p ...>, </p>
        s = re.sub(r"<p\b[^>]*>", "", s, flags=re.IGNORECASE)
        s = re.sub(r"</p>", "", s, flags=re.IGNORECASE)
        return s

    # Check for <보기>
    # Format: ... <보기> ...
    # Remove boxing logic as per user request, but assume p-tag stripping is still desired.
    # Just render clean text.
    # if "<보기>" in text: ... (removed)

    text = strip_p_tags(text)
    text = text.replace("\n", "<br>")
    return mark_safe(text)


# 선지별 설명에서 허용하는 태그는 강조(<em>) 하나뿐이다.
# 관리자가 넣는 값이지만 그대로 |safe로 흘리면 실수나 붙여넣기로
# 스크립트가 섞여 들어갈 수 있어, 나머지는 모두 글자로 만든다.
@register.filter
def choice_note(value, subject=None):
    """선지별 설명.

    <em>으로 감싼 핵심어 중 용어 사전에 있는 것만 점선을 긋고,
    누르면 아래에서 뜻을 보여 준다. 사전에 없는 말은 밑줄 없이 그냥 둔다.
    """
    if not value:
        return ""
    out = escape(value)                       # 우선 전부 무해하게 만들고
    out = out.replace("&lt;em&gt;", "<em>")   # 강조만 되살린다
    out = out.replace("&lt;/em&gt;", "</em>")
    out = _italicize(out)                     # *학명* -> 기울임
    out = _link_terms(out, subject)           # 사전에 있는 말만 점선 링크로
    # 형광줄이 줄마다 이어지려면 인라인 요소여야 한다.
    # 블록(div)에 배경을 걸면 첫 줄에만 칠해진다
    return mark_safe('<span class="hl">' + _latin_to_italic(out) + '</span>')


def _term_lookup(subject_name):
    """{낱말: 용어 id}. 과목별로 한 번만 만들어 둔다."""
    from django.core.cache import cache

    key = "choice_note_terms_%s" % (subject_name or "_all")
    got = cache.get(key)
    if got is not None:
        return got

    from glossary.models import Term

    qs = Term.objects.all()
    if subject_name:
        qs = qs.filter(subjects__name=subject_name)
    got = {w: i for i, w in qs.values_list("id", "word")}
    cache.set(key, got, 60 * 30)
    return got


def _link_terms(text, subject_name):
    """<em>핵심어</em> 중 사전에 있는 것만 누를 수 있게 바꾼다."""
    import re

    lookup = _term_lookup(subject_name)
    if not lookup:
        return re.sub(r"</?em>", "", text)

    def repl(m):
        inner = m.group(1)
        # 안에 <i> 같은 것이 섞여 있으면 글자만 뽑아 찾는다
        plain = re.sub(r"<[^>]+>", "", inner).strip()

        tid = lookup.get(plain)
        if tid is not None:
            return '<a class="term-link" data-term="%d">%s</a>' % (tid, inner)

        # 통째로는 없어도 안에 사전 낱말이 들어 있는 경우가 많다.
        # "나출자낭(표징)" -> "나출자낭", "표징이 나타나지 않습니다" -> "표징"
        # 태그가 섞인 것은 자리를 옮기기 어려우니 건드리지 않는다
        if "<" not in inner:
            best = None
            for word, wid in lookup.items():
                if len(word) < 2 or word not in inner:
                    continue
                if best is None or len(word) > len(best[0]):
                    best = (word, wid)
            if best:
                word, wid = best
                i = inner.index(word)
                return "%s<a class=\"term-link\" data-term=\"%d\">%s</a>%s" % (
                    inner[:i], wid, word, inner[i + len(word):]
                )

        return inner                  # 사전에 없으면 표시하지 않는다

    return re.sub(r"<em>(.*?)</em>", repl, text, flags=re.S)


# 선지 본문에도 용어 사전에 있는 말을 점선으로 잇는다.
# 설명(choice_note)과 달리 <em> 표시가 없으므로 글에서 직접 찾는다.
@register.filter
def choice_terms(value, subject=None):
    """선지 본문. 사전에 있는 낱말에 점선을 긋는다.

    선지에는 <i>(학명)나 <sup> 같은 태그가 드물게 섞여 있다.
    태그 안쪽은 건드리지 않고 글자 부분만 바꾼다.
    """
    import re

    from django.utils.safestring import mark_safe

    if not value:
        return ""

    text = str(value)
    lookup = _term_lookup(subject)
    if not lookup:
        return mark_safe(text)

    pattern = _term_pattern(subject)
    if pattern is None:
        return mark_safe(text)

    def link(seg):
        def repl(m):
            w = m.group(0)
            return '<a class="term-link" data-term="%d">%s</a>' % (lookup[w], w)

        return pattern.sub(repl, seg)

    # 태그(<i> 등)는 그대로 두고 그 사이의 글자만 바꾼다
    out = []
    pos = 0
    for m in re.finditer(r"<[^>]+>", text):
        out.append(link(text[pos:m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(link(text[pos:]))
    return mark_safe("".join(out))


def _term_pattern(subject_name):
    """과목별 용어를 한 번에 찾는 정규식. 긴 낱말이 먼저 걸리게 한다."""
    import re

    from django.core.cache import cache

    key = "choice_terms_re_%s" % (subject_name or "_all")
    got = cache.get(key)
    if got is not None:
        return re.compile(got) if got else None

    lookup = _term_lookup(subject_name)
    # 한 글자짜리는 아무 데나 걸려 방해가 된다
    words = sorted((w for w in lookup if len(w) >= 2), key=len, reverse=True)
    if not words:
        cache.set(key, "", 60 * 30)
        return None

    src = "|".join(re.escape(w) for w in words)
    cache.set(key, src, 60 * 30)
    return re.compile(src)


# 학명은 형광펜이 아니라 기울임으로 쓰는 것이 관례다.
# 모델이 <em>Exobasidium</em> 처럼 감싸 보낸 것을 바로잡는다.
def _latin_to_italic(text):
    out = []
    for i, chunk in enumerate(text.split("<em>")):
        if i == 0:
            out.append(chunk)
            continue
        inner, sep, rest = chunk.partition("</em>")
        if sep and _looks_latin(inner, rest):
            out.append("<i>" + inner + "</i>" + rest)
        else:
            out.append("<em>" + chunk)
    return "".join(out)


def _looks_latin(s, after=""):
    """라틴 학명처럼 보이는지 가린다.

    Bioventing 같은 기술 용어까지 기울이지 않도록, 학명의 두 가지
    전형만 인정한다.
      · 속명 + 종소명   (Taphrina wiesneri)
      · 속명 + spp./sp. (Exobasidium spp.)
    """
    s = s.strip()
    if not s or not s[0].isupper():
        return False
    for ch in s:
        # 한글이 섞이면 학명이 아니다
        if not (ch.isascii() and (ch.isalpha() or ch in " .-")):
            return False

    words = s.split()
    if len(words) >= 2 and words[1][:1].islower():
        return True                        # 속명 + 종소명
    if len(words) == 1:
        # 뒤에 spp. 이나 sp. 가 붙는 속명 표기
        return after.lstrip()[:4].rstrip(".").lower() in ("spp", "sp")
    return False


def _italicize(text):
    """*Xanthomonas citri* 처럼 별표로 감싼 학명을 기울임으로 바꾼다.

    별표가 짝을 이루지 않거나 안쪽이 비면 원문 그대로 둔다.
    (곱셈 기호 2 * 3 이나 **굵게** 를 건드리지 않기 위해서다)
    """
    parts = text.split("*")
    if len(parts) < 3 or len(parts) % 2 == 0:
        return text                       # 짝이 안 맞으면 손대지 않는다
    out = [parts[0]]
    for i in range(1, len(parts), 2):
        inner = parts[i]
        # 빈 칸이거나 공백으로 시작·끝나면 강조가 아니라고 본다
        if not inner.strip() or inner != inner.strip():
            return text
        out.append("<i>" + inner + "</i>")
        out.append(parts[i + 1])
    return "".join(out)
