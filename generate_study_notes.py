"""
범용 쪽집게 노트 생성 스크립트.
Gemini Filestore API (기본서)를 활용하여 문제 추출 → 목차 추출 → 문제 분류 → 장별 콘텐츠 생성.

사용법:
  python generate_study_notes.py <과목명>                    # 전체 실행
  python generate_study_notes.py <과목명> --phase phase1     # Step 0-2만
  python generate_study_notes.py <과목명> --phase chapter --chapter 3  # 3장만 생성
  python generate_study_notes.py <과목명> --phase phase3     # Step 4-5만
"""
import os, sys, json, time, re, logging, argparse

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from django.conf import settings
from fileSearchStore import GeminiStoreManager
from exam.models import Question, Subject

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# 과목별 설정
SUBJECT_CONFIG = {
    "수목생리학": {"search": "수목생리", "prefix": "physiology", "store": "수목생리학"},
    "산림토양학": {"search": "산림토양", "prefix": "soil", "store": "산림토양학"},
    "수목해충학": {"search": "수목해충", "prefix": "entomology", "store": "수목해충학"},
    "수목병리학": {"search": "수목병리", "prefix": "pathology", "store": "수목병리학"},
    "수목관리학": {"search": "수목관리", "prefix": "management", "store": "수목관리학"},
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("subject", help="과목명")
    parser.add_argument("--phase", choices=["all", "phase1", "chapter", "phase3"], default="all")
    parser.add_argument("--chapter", type=int, default=None, help="장 번호 (phase=chapter 시)")
    parser.add_argument("--force", action="store_true", help="기존 파일 덮어쓰기")
    return parser.parse_args()


args = parse_args()
SUBJECT_NAME = args.subject
config = SUBJECT_CONFIG.get(SUBJECT_NAME)
if not config:
    print(f"지원하지 않는 과목: {SUBJECT_NAME}")
    print(f"사용 가능: {', '.join(SUBJECT_CONFIG.keys())}")
    sys.exit(1)

PREFIX = config["prefix"]
STORE_NAME = config["store"]

QUESTIONS_FILE = os.path.join(BASE_DIR, f"{PREFIX}_questions.json")
CLASSIFICATION_FILE = os.path.join(BASE_DIR, f"{PREFIX}_classification.json")
TOC_FILE = os.path.join(BASE_DIR, f"{PREFIX}_toc.json")

# Gemini API 초기화
manager = GeminiStoreManager(api_key=settings.GEMINI_API_KEY)


def query_gemini(prompt, retries=3, delay=5):
    """Gemini Filestore API 쿼리 (재시도 포함)."""
    for attempt in range(retries):
        try:
            result = manager.query_store(STORE_NAME, prompt)
            if result and not result.startswith("Error"):
                return result
            log.warning(f"빈 응답 (시도 {attempt+1}/{retries}): {result[:100] if result else 'None'}")
        except Exception as e:
            log.warning(f"API 오류 (시도 {attempt+1}/{retries}): {e}")
        if attempt < retries - 1:
            time.sleep(delay * (attempt + 1))
    return None


def step0_extract_questions():
    """Step 0: DB에서 문제 추출."""
    if os.path.exists(QUESTIONS_FILE) and not args.force:
        with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data:
            log.info(f"기존 문제 파일 로드: {len(data)}개")
            return data

    log.info(f"=== Step 0: {SUBJECT_NAME} 문제 추출 ===")
    subject = Subject.objects.get(name__contains=config["search"])
    log.info(f"과목: {subject.name} (pk={subject.pk})")

    questions = Question.objects.filter(
        subject=subject,
        exam__round_number__gte=5,
        exam__round_number__lte=12,
    ).select_related("exam").order_by("exam__round_number", "number")

    data = []
    for q in questions:
        data.append({
            "round": q.exam.round_number,
            "number": q.number,
            "ref": f"{q.exam.round_number}-{q.number}",
            "content": q.content,
            "choice1": q.choice1,
            "choice2": q.choice2,
            "choice3": q.choice3,
            "choice4": q.choice4,
            "choice5": q.choice5,
            "answer": q.answer,
            "explanation": q.general_chat or "",
        })

    with open(QUESTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    log.info(f"추출 완료: {len(data)}문제 → {QUESTIONS_FILE}")
    from collections import Counter
    rc = Counter(q["round"] for q in data)
    for r in sorted(rc):
        log.info(f"  {r}회: {rc[r]}문제")

    return data


def step1_get_toc():
    """Step 1: 교재 목차 추출."""
    if os.path.exists(TOC_FILE) and not args.force:
        with open(TOC_FILE, "r", encoding="utf-8") as f:
            toc = json.load(f)
        if toc:
            log.info(f"기존 목차 로드: {len(toc)}개 장")
            return toc

    log.info("=== Step 1: 교재 목차 추출 ===")
    prompt = f"""이 교재({SUBJECT_NAME} 기본서)의 전체 목차를 알려주세요.

다음 JSON 형식으로 출력해 주세요:
[
  {{
    "chapter": 1,
    "title": "장 제목",
    "sections": [
      {{"section": "1.1", "title": "절 제목"}},
      {{"section": "1.2", "title": "절 제목"}}
    ]
  }},
  ...
]

모든 장과 절을 빠짐없이 포함해 주세요. JSON만 출력하세요."""

    result = query_gemini(prompt)
    if not result:
        log.error("목차 추출 실패")
        return None

    try:
        json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', result, re.DOTALL)
        if json_match:
            toc = json.loads(json_match.group(1))
        else:
            start = result.find('[')
            end = result.rfind(']') + 1
            toc = json.loads(result[start:end])
    except json.JSONDecodeError as e:
        log.error(f"목차 JSON 파싱 실패: {e}")
        log.info(f"원본 응답:\n{result[:2000]}")
        with open(TOC_FILE.replace('.json', '_raw.txt'), "w", encoding="utf-8") as f:
            f.write(result)
        return None

    with open(TOC_FILE, "w", encoding="utf-8") as f:
        json.dump(toc, f, ensure_ascii=False, indent=2)
    log.info(f"목차 저장: {len(toc)}개 장 → {TOC_FILE}")

    for ch in toc:
        log.info(f"  제{ch['chapter']}장. {ch['title']} ({len(ch.get('sections', []))}개 절)")

    return toc


def step2_classify_questions(toc, questions):
    """Step 2: 문제를 장별로 분류 (Gemini 기본서 활용)."""
    if os.path.exists(CLASSIFICATION_FILE) and not args.force:
        with open(CLASSIFICATION_FILE, "r", encoding="utf-8") as f:
            classification = json.load(f)
        if classification:
            total = sum(len(refs) for refs in classification.values())
            log.info(f"기존 분류 로드: {len(classification)}개 절, {total}개 문제")
            return classification

    log.info("=== Step 2: 문제 분류 ===")
    log.info(f"문제 수: {len(questions)}")

    toc_text = ""
    for ch in toc:
        toc_text += f"\n제{ch['chapter']}장. {ch['title']}\n"
        for sec in ch.get("sections", []):
            toc_text += f"  {sec['section']} {sec['title']}\n"

    classification = {}
    batch_size = 25

    for i in range(0, len(questions), batch_size):
        batch = questions[i:i+batch_size]
        batch_refs = [q["ref"] for q in batch]
        log.info(f"분류 중: {batch_refs[0]} ~ {batch_refs[-1]} ({len(batch)}문제)")

        q_text = ""
        for q in batch:
            q_text += f"\n[{q['ref']}] {q['content']}\n"
            for ci in range(1, 6):
                choice = q.get(f"choice{ci}", "")
                if choice:
                    q_text += f"  {'①②③④⑤'[ci-1]} {choice}\n"

        prompt = f"""아래는 나무의사 시험 {SUBJECT_NAME} 기출문제입니다.
이 교재({SUBJECT_NAME} 기본서)의 목차를 참고하여 각 문제가 어느 절(section)에 해당하는지 분류해 주세요.

=== 교재 목차 ===
{toc_text}

=== 기출문제 ===
{q_text}

다음 JSON 형식으로 출력하세요. 절 번호(예: "1.1", "2.3")를 키로, 해당 문제 ref 배열을 값으로:
{{
  "1.1": ["5-26", "5-30"],
  "2.3": ["6-28"],
  ...
}}

- 반드시 모든 문제({len(batch)}개)를 분류하세요.
- 가장 관련 깊은 절 하나에만 배정하세요.
- JSON만 출력하세요."""

        result = query_gemini(prompt)
        if not result:
            log.warning(f"배치 {i//batch_size + 1} 분류 실패, 건너뜀")
            continue

        try:
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', result, re.DOTALL)
            if json_match:
                batch_cls = json.loads(json_match.group(1))
            else:
                start = result.find('{')
                end = result.rfind('}') + 1
                batch_cls = json.loads(result[start:end])
        except json.JSONDecodeError as e:
            log.warning(f"배치 {i//batch_size + 1} JSON 파싱 실패: {e}")
            continue

        for section, refs in batch_cls.items():
            if section not in classification:
                classification[section] = []
            classification[section].extend(refs)

        time.sleep(2)

    with open(CLASSIFICATION_FILE, "w", encoding="utf-8") as f:
        json.dump(classification, f, ensure_ascii=False, indent=2)

    total = sum(len(refs) for refs in classification.values())
    log.info(f"분류 완료: {len(classification)}개 절, {total}/{len(questions)}개 문제")

    return classification


def step3_generate_chapter(ch_info, classification, questions_by_ref):
    """Step 3: 장별 콘텐츠 생성 (Gemini 기본서 활용)."""
    ch_num = ch_info["chapter"]
    ch_title = ch_info["title"]
    out_path = os.path.join(DATA_DIR, f"{PREFIX}_note_ch{ch_num}.md")

    if os.path.exists(out_path) and not args.force:
        with open(out_path, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) > 500:
            log.info(f"  제{ch_num}장 이미 생성됨 ({len(content.splitlines())}줄), 건너뜀")
            return out_path

    sections = ch_info.get("sections", [])

    ch_prefix = f"{ch_num}."
    ch_questions = []
    ch_section_refs = {}

    for section, refs in classification.items():
        if section.startswith(ch_prefix) or section == str(ch_num):
            ch_section_refs[section] = refs
            for ref in refs:
                if ref in questions_by_ref:
                    ch_questions.append(questions_by_ref[ref])

    log.info(f"  제{ch_num}장. {ch_title}: {len(sections)}개 절, {len(ch_questions)}개 관련 문제")

    section_groups = []
    current_group = []
    for sec in sections:
        current_group.append(sec)
        if len(current_group) >= 3:
            section_groups.append(current_group)
            current_group = []
    if current_group:
        section_groups.append(current_group)

    chapter_parts = [f"## 제{ch_num}장. {ch_title}\n"]

    for group_idx, group in enumerate(section_groups):
        sec_numbers = [s["section"] for s in group]
        log.info(f"    생성 중: {', '.join(sec_numbers)}")

        related_q_text = ""
        section_ref_map = {}
        for sec in group:
            sec_num = sec["section"]
            refs = ch_section_refs.get(sec_num, [])
            section_ref_map[sec_num] = refs
            for ref in refs:
                if ref in questions_by_ref:
                    q = questions_by_ref[ref]
                    related_q_text += f"\n[{ref}] {q['content']}\n"
                    for ci in range(1, 6):
                        choice = q.get(f"choice{ci}", "")
                        if choice:
                            related_q_text += f"  {'①②③④⑤'[ci-1]} {choice}\n"
                    ans = q.get("answer", [])
                    if isinstance(ans, list):
                        related_q_text += f"  정답: {','.join(str(a) for a in ans)}\n"
                    else:
                        related_q_text += f"  정답: {ans}\n"

        ref_info = ""
        for sec in group:
            sec_num = sec["section"]
            refs = section_ref_map.get(sec_num, [])
            if refs:
                ref_info += f"\n{sec_num}절 관련 문제: {', '.join(f'({r})' for r in refs)}"

        prompt = f"""교재({SUBJECT_NAME} 기본서)를 참고하여 아래 절의 핵심정리 노트를 작성해 주세요.

=== 작성 대상 ===
제{ch_num}장. {ch_title}
{chr(10).join(f'  {s["section"]} {s["title"]}' for s in group)}

=== 관련 기출문제 ===
{related_q_text if related_q_text else "(해당 절 관련 기출문제 없음)"}

=== 절별 관련 문제 배정 ===
{ref_info if ref_info else "(없음)"}

=== 작성 규칙 ===
1. 마크다운 형식: ### {sec_numbers[0]} 절 제목 → #### {sec_numbers[0]}.1 소제목 (필요시)
2. **교재형 서술문**으로 작성. 교재를 읽듯 자연스러운 문장으로 서술. 불렛(-)은 열거가 필요할 때만 사용.
3. 핵심 용어는 **볼드**로 강조.
4. 각 절 끝에 관련 문제가 있으면 반드시 **관련 문제**: (R-N) 형식으로 추가. 예: (5-26), (7-30).
5. 기출문제에 나온 핵심 내용을 빠짐없이 포함하되, 교재 내용을 바탕으로 더 풍부하게 서술.
6. 화학식은 유니코드 첨자(H₂O, CO₂ 등) 사용, LaTeX 사용 금지.
7. 절 제목(###)에 '핵심 정리' 라벨 붙이지 말 것.
8. 장 제목(##)은 이미 있으므로 작성하지 말 것. 절(###)부터 시작.

노트 마크다운만 출력하세요."""

        result = query_gemini(prompt)
        if result:
            lines = result.split('\n')
            filtered = []
            for line in lines:
                if line.strip().startswith(f"## 제{ch_num}장"):
                    continue
                if line.strip().startswith("```"):
                    continue
                filtered.append(line)
            chapter_parts.append('\n'.join(filtered).strip())
        else:
            log.warning(f"    {', '.join(sec_numbers)} 생성 실패")

        time.sleep(3)

    # 키워드 요약 테이블
    log.info(f"    키워드 요약 테이블 생성 중...")
    all_ch_refs = [r for refs in ch_section_refs.values() for r in refs]
    summary_prompt = f"""제{ch_num}장 '{ch_title}'의 핵심 키워드 요약 테이블을 작성해 주세요.

이 장에서 다룬 주요 내용(교재 기반)과 관련 기출문제를 고려하여 작성하세요.
관련 기출 문제 ref: {', '.join(f'({r})' for r in all_ch_refs)}

마크다운 테이블 형식으로 출력:
### 핵심 키워드 요약

| 키워드 | 핵심 포인트 |
|--------|------------|
| ... | ... |

15~25개 항목으로 작성. 시험에 자주 출제되는 핵심 내용 위주로.
테이블만 출력하세요."""

    summary_result = query_gemini(summary_prompt)
    if summary_result:
        summary_lines = summary_result.split('\n')
        summary_filtered = [l for l in summary_lines if not l.strip().startswith("```")]
        chapter_parts.append('\n'.join(summary_filtered).strip())

    full_content = '\n\n'.join(chapter_parts)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(full_content)

    line_count = len(full_content.splitlines())
    log.info(f"  제{ch_num}장 저장: {line_count}줄 → {out_path}")
    return out_path


def step4_verify_coverage(classification, questions):
    """Step 4: 커버리지 검증."""
    log.info("=== Step 4: 커버리지 검증 ===")
    all_refs = set(q["ref"] for q in questions)
    classified_refs = set()
    for refs in classification.values():
        classified_refs.update(refs)

    missing = all_refs - classified_refs
    extra = classified_refs - all_refs

    log.info(f"전체 문제: {len(all_refs)}")
    log.info(f"분류된 문제: {len(classified_refs)}")
    log.info(f"누락: {len(missing)} → {sorted(missing)[:20]}")
    if extra:
        log.info(f"초과(오분류): {len(extra)} → {sorted(extra)[:20]}")

    coverage = len(classified_refs & all_refs) / len(all_refs) * 100
    log.info(f"커버리지: {coverage:.1f}%")
    return missing


def step5_import_db():
    """Step 5: DB에 import."""
    log.info("=== Step 5: DB import ===")
    import glob as glob_mod

    subject = Subject.objects.get(name__contains=config["search"])
    from exam.models import StudyNote

    pattern = os.path.join(DATA_DIR, f"{PREFIX}_note_ch*.md")
    files = sorted(glob_mod.glob(pattern), key=lambda f: int(re.search(r"ch(\d+)", f).group(1)))

    if not files:
        log.warning(f"파일 없음: {pattern}")
        return

    log.info(f"발견된 파일: {len(files)}개")
    for idx, filepath in enumerate(files):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        m = re.match(r"## (제\d+장\.\s*.+)", content.split("\n")[0])
        title = m.group(1).strip() if m else f"제{idx+1}장"
        note, created = StudyNote.objects.update_or_create(
            subject=subject,
            order=idx + 1,
            defaults={"title": title, "content": content},
        )
        action = "생성" if created else "갱신"
        log.info(f"  [{action}] order={idx+1}: {title}")
    log.info(f"DB import 완료: {len(files)}개 노트")


def main():
    phase = args.phase

    if phase in ("all", "phase1"):
        log.info(f"===== {SUBJECT_NAME} Phase 1 (Step 0-2) =====")
        questions = step0_extract_questions()
        if not questions:
            log.error("문제 추출 실패, 종료")
            return
        toc = step1_get_toc()
        if not toc:
            log.error("목차 추출 실패, 종료")
            return
        classification = step2_classify_questions(toc, questions)
        if not classification:
            log.error("문제 분류 실패, 종료")
            return
        if phase == "phase1":
            log.info(f"Phase 1 완료. toc: {len(toc)}장")
            return

    if phase in ("all", "chapter"):
        # 캐시에서 로드
        with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
            questions = json.load(f)
        questions_by_ref = {q["ref"]: q for q in questions}
        with open(TOC_FILE, "r", encoding="utf-8") as f:
            toc = json.load(f)
        with open(CLASSIFICATION_FILE, "r", encoding="utf-8") as f:
            classification = json.load(f)

        if args.chapter is not None:
            # 특정 장만 생성
            ch_info = None
            for ch in toc:
                if ch["chapter"] == args.chapter:
                    ch_info = ch
                    break
            if ch_info:
                step3_generate_chapter(ch_info, classification, questions_by_ref)
            else:
                log.error(f"제{args.chapter}장을 찾을 수 없음")
            return
        else:
            # 전체 장 생성
            log.info(f"=== Step 3: 장별 콘텐츠 생성 ({len(toc)}개 장) ===")
            for ch_info in toc:
                step3_generate_chapter(ch_info, classification, questions_by_ref)
                time.sleep(2)

    if phase in ("all", "phase3"):
        with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
            questions = json.load(f)
        with open(CLASSIFICATION_FILE, "r", encoding="utf-8") as f:
            classification = json.load(f)

        step4_verify_coverage(classification, questions)
        step5_import_db()

        log.info("===== 완료 =====")
        import glob as glob_mod
        md_files = sorted(glob_mod.glob(os.path.join(DATA_DIR, f"{PREFIX}_note_ch*.md")))
        for f in md_files:
            with open(f, "r", encoding="utf-8") as fh:
                lines = len(fh.readlines())
            log.info(f"  {os.path.basename(f)}: {lines}줄")


if __name__ == "__main__":
    main()
