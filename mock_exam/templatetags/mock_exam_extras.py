from django import template

register = template.Library()


@register.filter
def is_checked(selected_choice, value):
    """
    Returns 'checked' if selected_choice matches value, else empty string.
    Usage: {{ mq.selected_choice|is_checked:1 }}
    """
    if selected_choice is not None and int(selected_choice) == int(value):
        return "checked"
    return ""
