
import os
import sys
import django
import re

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Set UTF-8 for Windows console redirection
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from exam.models import Question, Subject

def main():
    print("=== 산림토양학 화학식 표기 점검 ===")
    
    try:
        subject = Subject.objects.get(name="산림토양학")
    except Subject.DoesNotExist:
        subject = Subject.objects.filter(name__contains="토양").first()
        
    if not subject:
        print("과목을 찾을 수 없습니다.")
        return
        
    questions = Question.objects.filter(subject=subject)
    
    # Common chemical formulas in Soil Science that should use subscripts
    # Regex designed to catch 'ElementNumber' e.g. CO2, NO3, H2O, N2
    # Exclude common false positives like 'A1' (Horizon), 'B2', 'Q1', 'No1'
    # Actually 'No.1' usually has dot. 'NO3' is Nitrate.
    
    # Strategy: Find words starting with Capital, containing numbers.
    # We will look for sequences that look like formulas.
    
    # Updated Regex to capture NO3, CO2, H2O, Ca2+
    # Matches words starting with Capital, containing at least one digit.
    regex_formula = re.compile(r'\b[A-Z][a-zA-Z]*(?:\d)+[a-zA-Z0-9]*\b')
    
    # Exceptions (Soil Horizons or valid terms)
    # A1, A2, B1, B2, C1, C2, R, O1, O2... (Soil horizons are often written A1, not A₁)
    # But CO2, NO3 should be CO₂, NO₃.
    # Let's list everything found, effectively.
    
    suspicious_list = []
    
    for q in questions:
        # Check content and choices
        texts = [q.content] + [getattr(q, f'choice{i}') for i in range(1, 6)]
        
        for idx, text in enumerate(texts):
            if not text: continue
            
            matches = regex_formula.findall(text)
            for m in matches:
                # Filter out obvious horizons if user doesn't want them?
                # User asked specifically for NO3, N2.
                # Let's keep commonly known chemical patterns or just showing all.
                
                # Check if it's likely a chemical formula
                # If it ends with a number >= 2, likely a typo for subscript if it's a molecule
                # e.g. CO2, N2. 
                # If it's A1, it might be horizon.
                
                # Heuristic: if it contains O, H, N, C, P, S, Ca, Mg, K, Al, Fe, Mn typical elements
                # But 'A1' contains 'A' (verify element?). 'A' is not element. 'Al' is.
                
                # Let's just print finding.
                source = "문제 내용" if idx == 0 else f"보기 {idx}"
                
                # Clean marker
                suspicious_list.append({
                    'id': q.id,
                    'round': q.exam.round_number,
                    'number': q.number,
                    'source': source,
                    'match': m,
                    'context': text[:50] + "..." if len(text)>50 else text
                })

    print(f"총 발견된 패턴 수: {len(suspicious_list)}")
    print("="*60)
    print(f"{'문제':<10} {'위치':<10} {'발견된 문자':<15} {'설명(문맥)'}")
    print("="*60)
    
    # Group by potential formula?
    # Or just list distinct formulas found?
    # User might want to see WHERE to fix.
    
    # Let's count occurrences first to see diversity
    counts = {}
    for item in suspicious_list:
        m = item['match']
        counts[m] = counts.get(m, 0) + 1
        
    # Print distinct types first considering top frequency
    print(">> 주요 의심 패턴 빈도:")
    for k, v in sorted(counts.items(), key=lambda x: x[1], reverse=True):
        print(f" - {k}: {v}회")
        
    print("\n>> 상세 목록 (기출 회차/번호순):")
    # Sort by round/number
    suspicious_list.sort(key=lambda x: (int(x['round']), int(x['number'])))
    
    for item in suspicious_list:
        # Context highlighting
        ctx = item['context'].replace(item['match'], f"[{item['match']}]")
        print(f"{item['round']}회 {item['number']}번   {item['source']:<8} {item['match']:<15} {ctx}")

if __name__ == "__main__":
    main()
