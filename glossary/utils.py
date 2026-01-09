import re
from django.core.cache import cache
from .models import Term

def get_terms_pattern(subject_name):
    """
    해당 과목의 용어 패턴을 캐싱하여 반환
    반환: (compile된 regex 패턴, term_map 딕셔너리)
    """
    if not subject_name:
        return None, None
        
    cache_key = f'term_pattern_{subject_name}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return cached_data
    
    # 과목에 해당하는 용어들 가져오기 (긴 단어 우선)
    terms = Term.objects.filter(subjects__name=subject_name).values('id', 'word')
    
    if not terms:
        return None, None
        
    # 긴 단어부터 매칭되도록 정렬
    sorted_terms = sorted(terms, key=lambda t: len(t['word']), reverse=True)
    
    # {word: id} 맵핑 생성
    term_map = {t['word']: t['id'] for t in sorted_terms}
    
    # 정규식 패턴 생성 (특수문자 이스케이프)
    words = [re.escape(t['word']) for t in sorted_terms]
    pattern_str = r'(' + '|'.join(words) + r')'
    pattern = re.compile(pattern_str)
    
    result = (pattern, term_map)
    
    # 캐시에 저장 (타임아웃 없음, 명시적 삭제 전까지 유지)
    cache.set(cache_key, result, timeout=None)
    
    return result

def clear_subject_term_cache(subject_name):
    """특정 과목의 용어 패턴 캐시 삭제"""
    if subject_name:
        cache.delete(f'term_pattern_{subject_name}')
