from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def highlight_prefix(title):
    if title.startswith("[기본서]"):
        # 5 chars for "[기본서]"
        rest = title[5:]
        return mark_safe(f'<span style="color: #c92a2a;">[기본서]</span>{rest}')
    elif title.startswith("[기본서 질의]"):
        # Legacy support
        rest = title[8:]
        return mark_safe(f'<span style="color: #c92a2a;">[기본서 질의]</span>{rest}')
    elif title.startswith("[주치의]"):
        # 5 chars for "[주치의]"
        rest = title[5:]
        return mark_safe(f'<span style="color: #1e88e5;">[주치의]</span>{rest}')
    elif title.startswith("[나무주치의]"):
        # Legacy support
        rest = title[7:]
        return mark_safe(f'<span style="color: #1e88e5;">[나무주치의]</span>{rest}')
    return title
