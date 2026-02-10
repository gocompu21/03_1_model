from django import template
from django.utils.safestring import mark_safe
import markdown as md
import re

from functools import lru_cache

register = template.Library()


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
        
        # 3. Ensure table header starts on a new line
        text = text.replace(" | 구분 |", "\n| 구분 |")

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

        # 5.5. Remove leading 4-space indentation that causes code block rendering
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
