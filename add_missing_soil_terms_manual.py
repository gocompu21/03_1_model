
import os
import sys
import django

sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from glossary.models import Term, Subject

def main():
    print("=== 산림토양학 용어 수동 추가 ===")
    
    target_subject_name = "산림토양학"
    try:
        subject = Subject.objects.get(name=target_subject_name)
    except Subject.DoesNotExist:
        subject = Subject.objects.filter(name__contains="토양").first()
        
    if not subject:
        print("산림토양학 과목을 찾을 수 없습니다.")
        return
        
    print(f"대상 과목: {subject.name}")

    raw_terms = """
Al
Al2O3
Al3
AlOOH
Alfisols
Andisols
Bacillus
Beijerinckia
CL
CO
Ca
Ca2
CaMg
Cd
Cd2
Cl
Cu
Derxia
EDTA
Entisols
Fe
Fe2
FeO
FeO3
FeOOH
H2PO4
H2S
HPO4
Histosols
II
III
IV
K-
Klebsiella
Land
Mg
Mg2
Micrococcus
Mn
Mn-
Mo
Munsell
Mycobacter
N-
NH2
NH4
NO3
Na
Nitrocystis
Nitrosococcus
Nitrosospira
OH
Oxisols
PH
Phytoremidiation
SCL
SL
SiL
SiO2
TiO2
USDA
Ultisols
Zn
apatite
bentonite
dolomite
genus
incineration
interlayer spacing
land farming
macroaggregate
massive structrure
oxisols
각섬석
감람석
나트륨퍼센트
단립
단생
돌로마이트
매트릭
먼셀
버미큘라이트
벤조
벤토나이트
벽상구조
비료
산도
석영
속효성
스멕타이트
식물복원
안디졸
알로판
알피졸
앤디졸
엔티졸
염기불포화도
옥시졸
완효성
울티졸
유리화
인셉티졸
인회석
일라이트
장석
전기전도도
전이
질소량
토양경작
카올리나이트
코어
클로라이트
탄산마그네슘
탄산칼슘
할로이사이트
헤마타이트
황산칼슘
황화수소
휘석
히스토졸
"""
    
    term_list = [t.strip() for t in raw_terms.strip().split('\n') if t.strip()]
    
    count_new = 0
    count_linked = 0
    count_exist = 0
    
    for word in term_list:
        # Check if term exists (case-insensitive check might be good, but Term.word is standardized)
        # Using get_or_create to be safe
        term, created = Term.objects.get_or_create(word=word)
        
        if created:
            term.subjects.add(subject)
            print(f"[신규] {word}")
            count_new += 1
        else:
            if not term.subjects.filter(id=subject.id).exists():
                term.subjects.add(subject)
                print(f"[연결] {word}")
                count_linked += 1
            else:
                count_exist += 1
                
    print("="*30)
    print(f"작업 완료:")
    print(f"- 신규 추가: {count_new}")
    print(f"- 과목 연결: {count_linked}")
    print(f"- 이미 존재: {count_exist}")

if __name__ == "__main__":
    main()
