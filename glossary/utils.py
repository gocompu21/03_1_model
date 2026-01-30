import re
from django.core.cache import cache
from .models import Term
from functools import lru_cache

@lru_cache(maxsize=32)
def get_terms_pattern(subject_name):
    """
    해당 과목의 용어 패턴을 캐싱하여 반환
    반환: (compile된 regex 패턴, term_map 딕셔너리)
    메모리 캐시(lru_cache)를 1차로 사용하고, 없으면 Django 캐시, 없으면 DB 조회.
    """
    if not subject_name:
        return None, None
        
    cache_key = f'term_pattern_v2_{subject_name}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return cached_data
    
    # 과목에 해당하는 용어들 가져오기 (긴 단어 우선)
    # Term 객체를 직접 가져오고 reference_count를 미리 계산하여 캐싱
    from django.db.models import Count
    terms = Term.objects.filter(subjects__name=subject_name).annotate(
        reference_count=Count('references')
    )
    
    if not terms:
        return None, None
        
    # 긴 단어부터 매칭되도록 정렬 (메모리에서 정렬)
    # 쿼리셋을 리스트로 변환하여 캐싱 가능한 형태로 만듦
    terms_list = list(terms)
    sorted_terms = sorted(terms_list, key=lambda t: len(t.word), reverse=True)
    
    # {word: TermObject} 맵핑 생성
    term_map = {t.word: t for t in sorted_terms}
    
    # 정규식 패턴 생성 (특수문자 이스케이프)
    words = [re.escape(t.word) for t in sorted_terms]
    pattern_str = r'(' + '|'.join(words) + r')'
    pattern = re.compile(pattern_str)
    
    result = (pattern, term_map)
    
    # 캐시에 저장 (타임아웃 없음, 명시적 삭제 전까지 유지)
    cache.set(cache_key, result, timeout=None)
    
    return result

def clear_subject_term_cache(subject_name):
    """특정 과목의 용어 패턴 캐시 삭제"""
    # 메모리 캐시 삭제
    get_terms_pattern.cache_clear()
    
    if subject_name:
        cache.delete(f'term_pattern_v2_{subject_name}')
