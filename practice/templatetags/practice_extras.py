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
