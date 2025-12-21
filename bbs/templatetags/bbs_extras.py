from django import template
from django.utils.safestring import mark_safe
from django.utils import timezone
from datetime import timedelta

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


@register.filter
def compact_date(value):
    now = timezone.now()
    if value is None:
        return ""

    diff = now - value

    if diff < timedelta(minutes=1):
        return "방금 전"
    elif diff < timedelta(hours=1):
        return f"{diff.seconds // 60}분 전"
    elif diff < timedelta(days=1):
        return f"{diff.seconds // 3600}시간 전"
    elif diff < timedelta(days=7):
        return f"{diff.days}일 전"
    elif diff < timedelta(days=365):
        return value.strftime("%m/%d")
    else:
        return value.strftime("%Y/%m/%d")


@register.filter
def elided_page_range(page_obj):
    """
    Returns a list of pages to be displayed in pagination, including ellipsis.
    Centered around the current page of the passed page_obj.
    """
    if not page_obj:
        return []
    paginator = page_obj.paginator
    # on_each_side=3 ensures that for page 4, we see 1..7.
    return paginator.get_elided_page_range(
        number=page_obj.number, on_each_side=3, on_ends=1
    )
