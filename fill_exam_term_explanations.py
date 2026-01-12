"""
기출문제에 등장한 용어 중 해설이 없거나 짧은 용어를 기본서에서 조회하여 업데이트하는 스크립트.

사용법:
    python fill_exam_term_explanations.py [--max-length 100] [--dry-run] [--limit 10]

옵션:
    --max-length : 이 길이 이하의 content를 가진 용어만 대상으로 함 (기본값: 100)
    --dry-run    : 실제 DB 업데이트 없이 대상 용어만 출력
    --limit      : 처리할 최대 용어 개수 (기본값: 전체)
"""
import os
import sys
import time
import argparse
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from django.db.models import Q
from glossary.models import Subject, Term, TermReference

# fileSearchStore import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fileSearchStore import GeminiStoreManager


def get_exam_terms_with_short_content(max_length: int):
    """
    기출문제(Question)에 등장한 용어 중 content가 비어있거나 max_length 이하인 용어를 반환.
    TermReference에서 source_type='question'인 용어만 대상.
    """
    # TermReference에서 기출문제에 링크된 용어 ID 수집
    exam_term_ids = TermReference.objects.filter(
        source_type='question'
    ).values_list('term_id', flat=True).distinct()
    
    # 해당 용어들 중 content가 비어있거나 짧은 것만 필터
    terms = Term.objects.filter(
        id__in=exam_term_ids
    ).filter(
        Q(content__isnull=True) | Q(content='') | Q(content__regex=r'^.{0,' + str(max_length) + r'}$')
    ).order_by('word')
    
    return terms


def main():
    parser = argparse.ArgumentParser(description='기출문제 용어 해설 채우기')
    parser.add_argument('--max-length', type=int, default=100, 
                        help='이 길이 이하의 content를 가진 용어만 대상 (기본값: 100)')
    parser.add_argument('--dry-run', action='store_true',
                        help='실제 업데이트 없이 대상 용어만 출력')
    parser.add_argument('--limit', type=int, default=None,
                        help='처리할 최대 용어 개수')
    parser.add_argument('--wait', type=int, default=60,
                        help='API 호출 간 대기 시간(초) (기본값: 60)')
    args = parser.parse_args()

    print("=" * 60)
    print("기출문제 용어 해설 자동 채우기")
    print("=" * 60)
    print(f"  대상: content 길이 <= {args.max_length}자")
    print(f"  Dry-run: {args.dry_run}")
    print(f"  Limit: {args.limit or '전체'}")
    print(f"  Wait: {args.wait}초")
    print()

    # 1. 대상 용어 조회
    terms = get_exam_terms_with_short_content(args.max_length)
    
    if args.limit:
        terms = terms[:args.limit]
    
    total = len(terms)
    print(f"📋 대상 용어: {total}개")
    
    if total == 0:
        print("✅ 업데이트할 용어가 없습니다.")
        return
    
    # 대상 용어 목록 출력
    print("\n[대상 용어 목록]")
    for i, term in enumerate(terms, 1):
        content_preview = (term.content or '')[:30].replace('\n', ' ')
        print(f"  {i}. {term.word} (현재: {len(term.content or '')}자) - \"{content_preview}...\"")
    
    if args.dry_run:
        print("\n🔍 Dry-run 모드이므로 여기서 종료합니다.")
        return
    
    # 사용자 확인
    print()
    confirm = input(f"⚠️ {total}개 용어에 대해 기본서 조회를 시작하시겠습니까? (y/N): ")
    if confirm.lower() != 'y':
        print("취소되었습니다.")
        return

    # 2. GeminiStoreManager 초기화
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in settings.")
        return
    
    manager = GeminiStoreManager(api_key=api_key)
    print("\n✅ GeminiStoreManager 초기화 완료")
    
    # 타겟 스토어 (retry_terms.py와 동일하게 수목병리학 고정)
    target_store = "수목병리학"
    
    # 스토어가 없을 때만 동기화
    if target_store not in manager.stores or not manager.stores[target_store]:
        print("🔄 스토어 동기화 중...")
        manager.sync_all_stores()
    print(f"✅ 스토어 준비 완료: {target_store}")
    print()

    # 3. 각 용어 처리
    success_count = 0
    error_count = 0
    skip_count = 0

    for idx, term in enumerate(terms, 1):
        try:
            # 기본서에 질의 (retry_terms.py와 동일한 프롬프트)
            prompt = f"{term.word}에 대해 설명해주세요."
            print(f"[{idx}/{total}] 조회 중: {term.word}")
            
            response = manager.query_store(target_store, prompt)
            
            # 오류 응답이 아닌 경우에만 업데이트 (retry_terms.py 로직)
            if "429" not in response and "Error" not in response and len(response) > 100:
                term.content = response
                term.save()
                success_count += 1
                print(f"  -> 업데이트 완료 ({len(response)}자)")
            else:
                error_count += 1
                print(f"  -> 오류: {response[:50] if response else 'None'}...")
                
        except Exception as e:
            print(f"  -> 예외: {e}")
            error_count += 1
        
        # API 할당량 초과 방지를 위한 대기 (항상 60초)
        print(f"  -> {args.wait}초 대기...")
        time.sleep(args.wait)

    # 4. 결과 요약
    print("\n" + "=" * 60)
    print("📊 처리 결과")
    print("=" * 60)
    print(f"  ✅ 성공: {success_count}개")
    print(f"  ❌ 실패: {error_count}개")
    print(f"  ⏭️ 건너뜀: {skip_count}개")
    print(f"  📋 총 대상: {total}개")


if __name__ == "__main__":
    main()
