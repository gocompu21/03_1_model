# -*- coding: utf-8 -*-
"""
농약학 PDF에서 추출한 용어를 수목관리학 과목에 등록하는 배치 스크립트
"""
import sqlite3
import os

# 프로젝트 루트로 이동
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 용어 목록 (한글용어, 영문용어/설명)
TERMS = [
    # 독성 관련
    ("가비중", "bulk density"),
    ("가수분해", "hydrolysis"),
    ("감수성", "susceptibility"),
    ("검량식", "calibration curve"),
    ("검출기", "detector"),
    ("검화가", "saponification value"),
    ("경감제", "safener"),
    ("경구독성", "oral toxicity"),
    ("경피독성", "dermal toxicity"),
    ("계면활성제", "surface-active agent, surfactant"),
    ("고령토", "kaolin"),
    ("고리개열", "aromatic ring opening"),
    ("고속살포기", "speed sprayer, SS기"),
    ("고정상", "stationary phase"),
    ("고착성", "tenacity"),
    ("고착제", "sticking agent"),
    ("곤충 페로몬제", "insect pheromone"),
    ("공기압축식 살포기", "compressed air sprayer"),
    ("과립수화제", "water dispersible granule"),
    ("과립훈연제", "smoke pellet, FW"),
    ("과실방부제", "stored fruit protectant"),
    ("관주법", "drenching"),
    ("광합성", "photosynthesis"),
    ("괴사", "necrosis"),
    ("교차저항성", "cross resistance"),
    ("교호사용", "alternative use"),
    ("구리제", "copper compound"),
    ("규제물질 목록화제도", "negative list system, NLS"),
    ("규조토", "diatomaceous earth"),
    ("글루타민", "glutamine"),
    ("급성경구독성", "acute oral toxicity"),
    ("급성경피독성", "acute dermal toxicity"),
    ("급성독성", "acute toxicity"),
    ("급성흡입독성", "acute inhalation toxicity"),
    ("기계수용체", "stretch receptor"),
    ("기기 분석", "determination"),
    ("기체크로마토그래피", "gas chromatography"),
    ("기체크로마토그래피-질량분석법", "GC-MS"),
    ("기피물질", "repellent"),
    ("기피제", "repellent agent"),
    ("기형과", "malformed fruit"),

    # ㄴ
    ("나트륨펌프", "sodium pump"),
    ("낙과", "fruit drop"),
    ("납석", "pyrophyllite"),
    ("내부표준법", "internal standardization"),
    ("네오아소진", "neoasozin"),
    ("노출량", "exposure dose"),
    ("녹색혁명", "green revolution"),
    ("농약", "pesticide"),
    ("농약량", "median lethal dose, LD50"),
    ("농업용 항생제", "antibiotics for agriculture"),
    ("농작업자 농약 노출허용량", "allowable operator exposure level"),
    ("뇌혈액 관문", "brain blood barrier, BBB"),

    # ㄷ
    ("다년생 잡초", "perennial weed"),
    ("다량분석", "macro analysis"),
    ("다성분분석법", "multiresidue analytical method"),
    ("다제내성", "multidrug resistance"),
    ("도포법", "coating method"),
    ("도포제", "paste"),
    ("독먹이", "bait concentrate"),
    ("동력 살포기", "power sprayer"),
    ("드론", "drone sprayer"),

    # ㄹ
    ("라이아노딘", "ryanodine"),

    # ㅁ
    ("만성독성", "chronic toxicity"),
    ("만성중독", "chronic poisoning"),
    ("머무름 시간", "retention time, tR"),
    ("멜라닌", "melanin"),
    ("몬모릴론석", "montmorillonite"),
    ("무기화 과정", "mineralization"),
    ("무독화", "detoxication"),
    ("무인멀티콥터", "unmanned multicopter"),
    ("무인헬리콥터", "unmanned helicopter"),
    ("미량분석", "micro analysis, trace analysis"),
    ("미량살포법", "ultra-low-volume spraying, ULV"),
    ("미량살포액제", "ultra-low volume liquid, UL"),
    ("미립제", "microgranule, MG"),
    ("미분제", "Ho-dust, GP"),
    ("미세소관", "microtubule, MT"),
    ("미셀", "micelle"),
    ("미스트법", "mist spraying"),
    ("미탁제", "micro-emulsion, ME"),

    # ㅂ
    ("바이러스방제제", "virucide"),
    ("반복성", "repeatability"),
    ("반수치사량", "median lethal dose, LD50"),
    ("반침투성", "semi-systemic"),
    ("발색단", "chromophore"),
    ("발아전 처리제", "pre-emergence herbicide"),
    ("발아후 처리제", "post-emergence herbicide"),
    ("발암성", "carcinogenicity"),
    ("방향족 아미노산", "aromatic amino acid"),
    ("배액 조제법", "spray mixture preparation"),
    ("배치 선택성", "placement selectivity"),
    ("백화", "chlorosis/bleaching"),
    ("변이원성", "mutagenicity"),
    ("변태과정", "metamorphosis"),
    ("병의 삼각형", "disease triangle"),
    ("보르도액", "Bordeaux mixture"),
    ("보조제", "supplemental agent, adjuvant"),
    ("보호살균제", "protectant fungicide"),
    ("복합기능 산화효소", "mixed function oxidase, mfo"),
    ("복합저항성", "multiple resistance"),
    ("명반응", "light reaction"),
    ("부착량", "deposit"),
    ("부착성", "adherence, adhesiveness"),
    ("분광광도법", "spectrophotometry"),
    ("분극", "polarization"),
    ("분말도", "particle size"),
    ("분무법", "spraying"),
    ("분산성액제", "dispersible concentrate, DC"),
    ("분산제", "dispersing agent"),
    ("분의법", "dusting"),
    ("분제", "dust, dispersible powder, DP"),
    ("분해방지제", "stabilizer"),
    ("불꽃염광검출기", "flame photometric detector, FPD"),
    ("불꽃이온화검출기", "flame ionization detector, FID"),
    ("불완전변태", "incomplete metamorphosis"),
    ("불임화제", "chemasterilant, sterilant"),
    ("브라운 운동", "Brownian motion"),
    ("비대성장", "secondary growth"),
    ("비선택성 제초제", "nonselective herbicide"),
    ("비점오염원", "non-point source"),

    # ㅅ
    ("사이토카이닌류", "cytokinins"),
    ("산가", "acid value"),
    ("산소첨가효소", "monooxygenase"),
    ("살균제", "fungicides"),
    ("살립법", "aerial spraying"),
    ("살분법", "dusting method"),
    ("살선충제", "nematocides"),
    ("살어제", "piscicides"),
    ("살연체동물제", "molluscicides"),
    ("살응애제", "acaricides, miticides"),
    ("살조류제", "algicide"),
    ("살조제", "avicides"),
    ("살충제", "insecticide"),
    ("살포액", "spray solution"),
    ("상표명", "trade name"),
    ("생리적 선택성", "physiological selectivity"),
    ("생리적 요인", "physiological factor"),
    ("생물농약", "biopesticide"),
    ("생물농축", "bioconcentration"),
    ("생물농축계수", "bioconcentration factor, BCF"),
    ("생산단계농약 잔류허용기준", "PHRL"),
    ("생태적 선택성", "ecological selectivity"),
    ("생화학적 선택성", "biochemical selectivity"),
    ("생화학적 요인", "biochemical factor"),
    ("서방형 농약제형", "controlled release formulation"),
    ("석회유황합제", "lime sulfur"),
    ("선도물질", "lead compound"),
    ("선발물질", "selective agent"),
    ("선충", "nematode"),
    ("선택계수", "selection coefficient"),
    ("선택독성", "selective toxicity"),
    ("선택성", "selectivity"),
    ("선택성 제초제", "selective herbicide"),
    ("세균방제제", "bacteriocide"),
    ("세립제", "fine granule, FG"),
    ("소해시험", "dissection test"),
    ("수면부상성 입제", "water floating granule, UG"),
    ("수면전개제", "spreading oil, SO"),
    ("수산화 반응", "hydroxylation"),
    ("수상돌기", "dendrite"),
    ("수압식 살포기", "hydraulic sprayer"),
    ("수용기", "receptor"),
    ("수용제", "water soluble powder, SP"),
    ("수중붕괴성", "water disintegrability"),
    ("수화성", "wettability"),
    ("수화제", "wettable powder, WP"),
    ("수확 후 처리제", "postharvest treatment"),
    ("스마트 팜", "smart farm"),
    ("습윤성", "wettability"),
    ("습전계수", "spreading coefficient"),
    ("습전성", "spreading property"),
    ("승홍", "mercuric chloride"),
    ("시냅스", "synapse"),
    ("시료 주입구", "sample inlet"),
    ("시료 추출", "extraction"),
    ("식독제", "stomach poison"),
    ("식물생장억제제", "plant growth retardant"),
    ("식물생장조절제", "plant growth regulator, PGR"),
    ("식이섭취량", "dietary intake"),
    ("신경근 접합부", "neuromuscular junction"),
    ("신경전달물질", "neurotransmitter"),
    ("신속성", "rapidity"),

    # ㅇ
    ("아급성독성", "subacute toxicity"),
    ("아만성독성", "subchronic toxicity"),
    ("아브시스산", "abscisic acid"),
    ("아세틸 CoA 카르복실화 효소", "acetyl CoA carboxylase, ACCase"),
    ("아세틸콜린에스테라제", "acetylcholinesterase"),
    ("안전계수", "safety factor, SF"),
    ("안전사용기준", "safe use standard"),
    ("안점막 자극성 시험", "primary eye irritation test"),
    ("알킬화제", "alkylating agent"),
    ("압출조립법", "extrusion"),
    ("액상수화제", "suspension concentrate, SC"),
    ("액제", "soluble concentrate, SL"),
    ("액체크로마토그래피", "high-performance liquid chromatography, HPLC"),
    ("액체크로마토그래피-질량분석법", "LC-MS"),
    ("약반", "pesticide spot"),
    ("약제저항성", "pesticide resistance"),
    ("약해", "phytotoxicity"),
    ("약해경감제", "herbicide safener"),
    ("양이온치환용량", "cation exchange capacity"),
    ("양적 저항성", "quantitative resistance"),
    ("에틸렌 발생제", "ethylene generator"),
    ("연동분석법", "hyphenated techniques"),
    ("연무기", "fog machine"),
    ("연무법", "fogging"),
    ("연무제", "fog formulation"),
    ("열전도도검출기", "thermal conductivity detector, TCD"),
    ("염색체 이상", "chromosome aberration"),
    ("엽록소", "chlorophyll"),
    ("오일제", "oil miscible liquid, OL"),
    ("오차", "error"),
    ("옥신", "auxin"),
    ("옥신류", "auxins"),
    ("완전변태", "complete metamorphosis"),
    ("외부표준법", "external standardization"),
    ("용량계수", "capacity factor"),
    ("용매", "solvent"),
    ("유기염소계", "organochlorine"),
    ("유기인계", "organophosphorus"),
    ("유동충조립법", "fluidized bed granulation"),
    ("유약 호르몬", "juvenile hormone"),
    ("유인물질", "attractant"),
    ("유인제", "attractant agent"),
    ("유인항공기", "manned aircraft"),
    ("유전자조작생물체", "genetically modified organism"),
    ("유제", "emulsifiable concentrate, EC"),
    ("유충호르몬", "juvenile hormone, JH"),
    ("유탁제", "emulsion, oil in water, EW"),
    ("유화성", "emulsifiability"),
    ("유화액", "emulsion"),
    ("유화제", "emulsifier"),
    ("유효성분", "active ingredient"),
    ("유황", "sulfur"),
    ("응애", "mite"),
    ("이동상", "mobile phase"),
    ("이동상 이송장치", "solvent delivery pump"),
    ("이론적 최대섭취허용량", "theoretical maximum daily intake, TMDI"),
    ("이행형 제초제", "translocation herbicide"),
    ("인력 살포기", "manual sprayer"),
    ("일률기준", "uniform limit"),
    ("일반명", "common name"),
    ("임실장애", "fertility stress"),
    ("입경 분석", "particle size distribution analysis"),
    ("입경분석기", "particle size analyzer"),
    ("입상수화제", "water dispersible granule, WG"),
    ("입제", "granule, GR"),

    # ㅈ
    ("자동시료주입기", "autosampler"),
    ("자외가시광 흡광검출기", "UV/VIS absorption detector, UVD"),
    ("작용기작", "mode of action"),
    ("잔류성 유기오염물질", "persistent organic pollutants"),
    ("잔류성 접촉독제", "residual contact poison"),
    ("잔류허용기준", "maximum residue limit, MRL"),
    ("잔류허용한계", "permissible level"),
    ("잡초", "weed"),
    ("잡초발생 후 처리제", "post-emergence herbicides"),
    ("재현성", "repeatability"),
    ("재확인", "confirmation"),
    ("저니토", "sediment"),
    ("저비산분제", "driftless dust, DL"),
    ("저항성비", "resistance ratio, RR"),
    ("적정법", "titration"),
    ("전기영동법", "electrophoresis"),
    ("전기화학법", "electrochemistry"),
    ("전동조립법", "tumbling granulation"),
    ("전면살포법", "broadcast application"),
    ("전신복장노출법", "whole body dosimeter, WBD"),
    ("전신획득저항성", "systemic acquired resistance, SAR"),
    ("전자면적계산계", "integrator"),
    ("전자포획검출기", "electron capture detector, ECD"),
    ("전착제", "spreader"),
    ("점토", "clay"),
    ("접촉각", "contact angle"),
    ("접촉독제", "contact poison"),
    ("접촉형 제초제", "contact herbicide"),
    ("정량 분석", "quantitative analysis"),
    ("정밀성", "precision"),
    ("정상적 경작 형태", "good agricultural practice, GAP"),
    ("정성분석", "qualitative analysis"),
    ("정전기 살포법", "electrostatic application"),
    ("정제", "purification of the extract"),
    ("정지전위", "resting potential"),
    ("정확성", "accuracy"),
    ("제아틴", "zeatin"),
    ("제오라이트", "zeolite"),
    ("제제", "formulation"),
    ("제초제", "herbicides"),
    ("제충국", "Chrysanthnum cinerariaefolium, pyrethrum"),
    ("제품 분석", "product analysis"),
    ("제형", "formulation type"),
    ("종자소독제", "seed disinfectant"),
    ("종자처리액상수화제", "seed treatment SC"),
    ("종자처리수화제", "seed treatment WP"),
    ("종합적 방제", "integrated pest management, IPM"),
    ("중량법", "gravimetry"),
    ("중추신경계", "central nervous system"),
    ("증기압", "vapor pressure"),
    ("직접접촉독제", "direct contact poison"),
    ("증량제", "carrier, diluent"),
    ("증산류", "transpiration stream"),
    ("지발성 신경독성", "delayed neurotoxicity"),
    ("지베레린", "gibberellin"),
    ("지베렐린류", "gibberellins"),
    ("직접살균제", "eradicant"),
    ("질량분석법", "mass spectrometry"),
    ("질량 전하비", "mass to charge ratio"),
    ("질소-인검출기", "nitrogen-phosphorus detector, NPD"),
    ("질적 저항성", "qualitative resistance"),

    # ㅊ
    ("착색 저해", "color inhibition"),
    ("처리위치 선택성", "placement selectivity"),
    ("천연식물보호제", "natural plant protectant"),
    ("천적 살충제", "biological insecticide"),
    ("최기형성", "teratogenicity"),
    ("최대무독성용량", "no observable adverse effect level, NOAEL"),
    ("최대무작용량", "no observed effect level, NOEL"),
    ("추정 최대섭취허용량", "estimated maximum daily intake, EMDI"),
    ("축색", "axon"),
    ("취급 제한기준", "handling restriction standard"),
    ("친수-친유 균형비", "hydrophilic-lipophilic balance, HLB"),
    ("침지법", "dipping method"),
    ("침투성", "systemic property"),
    ("침투성 살충제", "systemic insecticide"),
    ("침투이행성", "systemic translocation"),

    # ㅋ
    ("카로티노이드", "carotenoid"),
    ("캡슐제", "encapsulated granule, CG"),
    ("캡슐현탁제", "capsule suspension, CS"),
    ("코드명", "code name"),
    ("콘쥬게이션", "conjugation"),
    ("큐티클", "cuticle"),
    ("크로마토그래피", "chromatography"),

    # ㅌ
    ("타감작용", "allelopathy"),
    ("탈공력제", "uncoupler"),
    ("탈분극", "depolarization"),
    ("탈피호르몬", "ecdysone"),
    ("탈할로겐화", "dehalogenation"),
    ("탈황화반응", "desulfuration"),
    ("토양소독제", "soil disinfectant"),
    ("토양잔류성 농약", "soil persistent pesticide"),
    ("토양혼화법", "soil incorporation"),
    ("투과성 계수", "permeability coefficient"),

    # ㅍ
    ("편차", "deviation"),
    ("표류비산", "drift"),
    ("표면산도", "surface acidity"),
    ("표면장력", "surface tension"),
    ("품목", "item"),
    ("품목명", "item name"),
    ("피복법", "coating"),
    ("피부감작성 시험", "skin sensitization test"),
    ("피부자극성 시험", "primary skin irritation test"),

    # ㅎ
    ("행동적 요인", "behavioral factor"),
    ("허용물질목록관리제도", "positive list system, PLS"),
    ("현수성", "suspensibility"),
    ("현음기관", "chordotonal organ"),
    ("현탁액", "suspension"),
    ("협력제", "synergist"),
    ("형태적 요인", "morphological factor"),
    ("형태학적 선택성", "morphological selectivity"),
    ("혼용", "tank mixing"),
    ("혼합제", "mixture"),
    ("혼화", "tank mixing"),
    ("화학명", "chemical name"),
    ("확전성", "spreading property"),
    ("환원반응", "reduction"),
    ("활동전위", "action potential"),
    ("활석", "talite"),
    ("활성제", "activator"),
    ("활성화", "activation"),
    ("활성화 기작", "activation mechanism"),
    ("훈연제", "smoke generator, FU"),
    ("훈증법", "fumigation"),
    ("훈증제", "fumigant"),
    ("휘산", "volatilization"),
    ("흡유가", "sorptive capacity"),
    ("흡입독성", "inhalation toxicity"),
    ("흡즙성", "sucking property"),
    ("흡착법", "impregnation"),
    ("희석배수", "dilution factor"),

    # 주요 농약 성분 (영문)
    ("Abamectin", "아바멕틴 - 살충제 성분"),
    ("Acetamiprid", "아세타미프리드 - 네오니코티노이드계 살충제"),
    ("Azoxystrobin", "아족시스트로빈 - 스트로빌루린계 살균제"),
    ("Bacillus thuringiensis", "바실러스 튜린지엔시스 - 미생물 살충제"),
    ("Carbendazim", "카벤다짐 - 벤지미다졸계 살균제"),
    ("Chlorpyrifos", "클로르피리포스 - 유기인계 살충제"),
    ("Clothianidin", "클로티아니딘 - 네오니코티노이드계 살충제"),
    ("DDT", "디디티 - 유기염소계 살충제"),
    ("Difenoconazole", "디페노코나졸 - 트리아졸계 살균제"),
    ("Glufosinate", "글루포시네이트 - 비선택성 제초제"),
    ("Glyphosate", "글리포세이트 - 비선택성 제초제"),
    ("Imidacloprid", "이미다클로프리드 - 네오니코티노이드계 살충제"),
    ("Mancozeb", "만코제브 - 디티오카바메이트계 살균제"),
    ("Paraquat", "파라쿼트 - 비피리딜리움계 제초제"),
    ("Pyrethroid", "피레스로이드 - 합성 피레스린계 살충제"),
    ("Tebuconazole", "테부코나졸 - 트리아졸계 살균제"),
    ("Thiamethoxam", "티아메톡삼 - 네오니코티노이드계 살충제"),

    # 1일 섭취허용량 등 주요 기준
    ("1일 섭취허용량", "acceptable daily intake, ADI"),
    ("1년생 잡초", "annual weed"),
    ("2년생 잡초", "biennial weed"),
]


def main():
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()

    # 1. 수목관리학 과목 확인/추가
    c.execute("SELECT id FROM glossary_subject WHERE name = ?", ("수목관리학",))
    result = c.fetchone()

    if result:
        subject_id = result[0]
        print(f"수목관리학 과목 이미 존재 (ID: {subject_id})")
    else:
        c.execute("INSERT INTO glossary_subject (name) VALUES (?)", ("수목관리학",))
        subject_id = c.lastrowid
        print(f"수목관리학 과목 추가됨 (ID: {subject_id})")

    conn.commit()

    # 2. 용어 등록
    added_count = 0
    skipped_count = 0
    updated_count = 0

    for word, content in TERMS:
        # 이미 존재하는지 확인
        c.execute("SELECT id FROM glossary_term WHERE word = ?", (word,))
        existing = c.fetchone()

        if existing:
            term_id = existing[0]
            # 이미 수목관리학과 연결되어 있는지 확인
            c.execute("""
                SELECT 1 FROM glossary_term_subjects
                WHERE term_id = ? AND subject_id = ?
            """, (term_id, subject_id))

            if not c.fetchone():
                # 수목관리학 과목 연결 추가
                c.execute("""
                    INSERT INTO glossary_term_subjects (term_id, subject_id)
                    VALUES (?, ?)
                """, (term_id, subject_id))
                updated_count += 1
            else:
                skipped_count += 1
        else:
            # 새 용어 추가
            c.execute("""
                INSERT INTO glossary_term (word, content, created_at, updated_at)
                VALUES (?, ?, datetime('now'), datetime('now'))
            """, (word, content))
            term_id = c.lastrowid

            # 수목관리학 과목 연결
            c.execute("""
                INSERT INTO glossary_term_subjects (term_id, subject_id)
                VALUES (?, ?)
            """, (term_id, subject_id))
            added_count += 1

    conn.commit()
    conn.close()

    print(f"\n=== 결과 ===")
    print(f"신규 추가: {added_count}개")
    print(f"과목 연결 추가: {updated_count}개")
    print(f"이미 존재 (스킵): {skipped_count}개")
    print(f"총 처리: {len(TERMS)}개")


if __name__ == "__main__":
    main()
