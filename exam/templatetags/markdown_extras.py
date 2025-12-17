from django import template
from django.utils.safestring import mark_safe
import markdown as md
import re

register = template.Library()


@register.filter(name="markdown")
def markdown_format(text):
    if not text:
        return ""
    # Pre-process to protect common LaTeX/MathJax commands from Markdown escaping
    # Markdown consumes one backslash, so we need double for it to survive into HTML for MathJax.
    if text:
        text = text.replace(r"\text", r"\\text")
        text = text.replace(r"\times", r"\\times")
        text = text.replace(r"\div", r"\\div")
        # Add other common commands as needed, or use regex for \[a-zA-Z] if safe

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
