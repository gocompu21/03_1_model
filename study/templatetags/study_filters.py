import re
from django import template

register = template.Library()


@register.filter
def summarize_question(content):
    """
    문제 내용을 간단한 주제로 요약합니다.
    예: "파이토플라스마의 설명 중 옳지 않은 것은?" -> "파이토플라스마 설명"
    """
    if not content:
        return ""
    
    # 불필요한 문구 제거 패턴
    remove_patterns = [
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
        r'으로 옳은 것은\?*',
        r'으로 옳지 않은 것은\?*',
        r'로 옳은 것은\?*',
        r'로 옳지 않은 것은\?*',
        r'중 옳은 것은\?*',
        r'중 옳지 않은 것은\?*',
        r'것은\?*$',
        r'무엇인가\?*$',
        r'다음 중 ',
        r'다음의 ',
        r'아래 중 ',
        r'\?$',
    ]
    
    text = content.strip()
    
    # HTML 태그 제거
    text = re.sub(r'<[^>]+>', '', text)
    
    # 줄바꿈을 공백으로
    text = re.sub(r'\s+', ' ', text)
    
    # 패턴 제거
    for pattern in remove_patterns:
        text = re.sub(pattern, '', text)
    
    # 앞부분만 추출 (최대 30자)
    text = text.strip()
    if len(text) > 30:
        # 단어 단위로 자르기
        words = text[:35].split()
        text = ' '.join(words[:-1]) if len(words) > 1 else text[:30]
    
    # 마지막 조사 정리
    text = re.sub(r'[은는이가을를의에]$', '', text.strip())
    
    return text.strip()
