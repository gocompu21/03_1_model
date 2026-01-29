"""
LaTeX 문법 오류 수정 스크립트
Term.content 필드에서 잘못된 LaTeX 문법을 찾아 수정합니다.

서버에서 실행:
    python fix_latex_syntax.py --dry-run   # 미리보기 (수정 안함)
    python fix_latex_syntax.py             # 실제 수정
"""
import os
import sys
import re
import django

# Django setup
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from glossary.models import Term

# LaTeX 수정 패턴들
FIXES = [
    # |text{ → \text{  (파이프를 백슬래시로)
    (r'\|text\{', r'\\text{'),
    
    # $\text{X}{12} → $\text{X}_{12}  (중괄호 앞에 밑줄 추가)
    (r'\\text\{([^}]+)\}\{(\d+)\}', r'\\text{\1}_{\2}'),
    
    # $\text{X}{Y}_ → $\text{X}_{Y}  (잘못된 밑줄 위치)
    (r'\\text\{([^}]+)\}\{([^}]+)\}_', r'\\text{\1}_{\2}'),
    
    # }\text → } \text  (누락된 공백)
    (r'\}\\text', r'} \\text'),
    
    # $$ 따옴표 문제 (잘못된 닫는 괄호)
    (r'\$\)(\$|\})', r'$'),
    
    # 연속된 $$ → 단일 $
    (r'\$\$(?!\$)', r'$'),
    
    # \text{O입니다 → \text{O}입니다  (닫는 중괄호 누락)
    (r'\\text\{([A-Za-z0-9]+)([가-힣])', r'\\text{\1}\2'),
]

def fix_latex(content):
    """LaTeX 문법 오류 수정"""
    if not content:
        return content, False
    
    original = content
    for pattern, replacement in FIXES:
        content = re.sub(pattern, replacement, content)
    
    return content, content != original

def main():
    dry_run = '--dry-run' in sys.argv
    
    print("=== LaTeX 문법 오류 수정 스크립트 ===")
    if dry_run:
        print("⚠️  미리보기 모드 (수정하지 않음)")
    print()
    
    # LaTeX 수식이 포함된 용어 찾기
    terms_with_latex = Term.objects.filter(content__contains='$').exclude(content='')
    print(f"📊 LaTeX 수식이 포함된 용어: {terms_with_latex.count()}개")
    
    fixed_count = 0
    fixed_terms = []
    
    for term in terms_with_latex:
        new_content, was_fixed = fix_latex(term.content)
        
        if was_fixed:
            fixed_count += 1
            fixed_terms.append({
                'id': term.id,
                'word': term.word,
                'before': term.content[:200],
                'after': new_content[:200]
            })
            
            if not dry_run:
                term.content = new_content
                term.save(update_fields=['content'])
    
    print(f"\n✅ 수정이 필요한 용어: {fixed_count}개")
    
    if fixed_terms:
        print("\n--- 수정 내용 미리보기 ---")
        for i, item in enumerate(fixed_terms[:10], 1):  # 최대 10개만 표시
            print(f"\n[{i}] {item['word']} (ID: {item['id']})")
            print(f"  Before: {item['before'][:100]}...")
            print(f"  After:  {item['after'][:100]}...")
        
        if len(fixed_terms) > 10:
            print(f"\n... 외 {len(fixed_terms) - 10}개 더 있음")
    
    if dry_run:
        print("\n💡 실제 수정하려면: python fix_latex_syntax.py")
    else:
        print(f"\n✅ {fixed_count}개 용어 수정 완료!")

if __name__ == "__main__":
    main()
