
import os
import sys
import django

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from exam.models import Question, Subject

def main():
    print("=== 산림토양학 화학식 표기 일괄 수정 ===")
    
    try:
        subject = Subject.objects.get(name="산림토양학")
    except Subject.DoesNotExist:
        subject = Subject.objects.filter(name__contains="토양").first()
        
    if not subject:
        print("과목을 찾을 수 없습니다.")
        return
        
    questions = Question.objects.filter(subject=subject)
    print(f"대상 문제 수: {questions.count()}")
    
    # Replacement Rules (Order Sensitive: Specific first)
    replacements = [
        # 1. Ions with charges (Positive)
        ("Ca2+", "Ca²⁺"),
        ("Mg2+", "Mg²⁺"),
        ("Cd2+", "Cd²⁺"),
        ("Fe2+", "Fe²⁺"),
        ("Fe3+", "Fe³⁺"),
        ("Al3+", "Al³⁺"),
        ("NH4+", "NH₄⁺"),
        ("K+", "K⁺"),
        ("Na+", "Na⁺"),
        ("H+", "H⁺"),
        ("Zn2+", "Zn²⁺"),
        ("Cu2+", "Cu²⁺"),
        ("Mn2+", "Mn²⁺"),
        
        # 2. Ions with charges (Negative)
        ("NO3-", "NO₃⁻"),
        ("H2PO4-", "H₂PO₄⁻"),
        ("HPO4 2-", "HPO₄²⁻"),
        ("HPO42-", "HPO₄²⁻"),
        ("SO4 2-", "SO₄²⁻"),
        ("SO42-", "SO₄²⁻"),
        ("CO3 2-", "CO₃²⁻"),
        ("CO32-", "CO₃²⁻"),
        ("OH-", "OH⁻"),
        ("Cl-", "Cl⁻"),
        
        # 3. Compounds / Molecules
        ("SiO2", "SiO₂"),
        ("TiO2", "TiO₂"),
        ("Al2O3", "Al₂O₃"),
        ("Fe2O3", "Fe₂O₃"),
        ("FeO3", "FeO₃"), # As found in log
        ("H2S", "H₂S"),
        ("CH4", "CH₄"),
        ("NH3", "NH₃"),
        ("(NH2)2CO", "(NH₂)₂CO"), # Urea
        ("H2O", "H₂O"),
        ("CO2", "CO₂"),
        ("N2O", "N₂O"),
        ("N2", "N₂"),
        ("O2", "O₂"),
        
        # 4. Partial matches (Context-less)
        ("NO3", "NO₃"),
        ("NH4", "NH₄"),
        ("NH2", "NH₂"),
        ("PO4", "PO₄"),
        ("SO4", "SO₄"),
        ("H2PO4", "H₂PO₄"),
        ("HPO4", "HPO₄"),
        
        # 5. Generic Ions (without explicit charge sign in text, e.g. "Al3 15cmol")
        ("Al3", "Al³⁺"),
        ("Fe3", "Fe³⁺"),
        ("Fe2", "Fe²⁺"),
        ("Ca2", "Ca²⁺"),
        ("Mg2", "Mg²⁺"),
        ("Cd2", "Cd²⁺"),
    ]
    
    count_updated = 0
    
    for q in questions:
        fields = ['content', 'choice1', 'choice2', 'choice3', 'choice4', 'choice5']
        changed = False
        
        for field in fields:
            original_text = getattr(q, field)
            if not original_text: continue
            
            new_text = original_text
            for old, new in replacements:
                if old in new_text:
                    new_text = new_text.replace(old, new)
            
            if original_text != new_text:
                setattr(q, field, new_text)
                changed = True
                # Print sample change
                if count_updated < 10: # Sample print
                    print(f"[{q.exam.round_number}회 {q.number}번] {field}: {original_text[:20]}... -> {new_text[:20]}...")
        
        if changed:
            q.save()
            count_updated += 1
            
    print("="*40)
    print(f"총 {count_updated}개의 문제가 수정되었습니다.")

if __name__ == "__main__":
    main()
