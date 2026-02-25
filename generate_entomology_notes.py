"""
수목해충학 쪽집게 노트 생성 스크립트.
Gemini Filestore API (기본서)를 활용하여 목차 추출 → 문제 분류 → 장별 콘텐츠 생성.
EC2에서 실행: python generate_entomology_notes.py
"""
import os, sys, json, time, re, logging

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from django.conf import settings
from fileSearchStore import GeminiStoreManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

QUESTIONS_FILE = os.path.join(BASE_DIR, "entomology_questions.json")
CLASSIFICATION_FILE = os.path.join(BASE_DIR, "entomology_classification.json")
TOC_FILE = os.path.join(BASE_DIR, "entomology_toc.json")

# Gemini API 초기화
manager = GeminiStoreManager(api_key=settings.GEMINI_API_KEY)
STORE_NAME = "수목해충학"


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


def step1_get_toc():
    """Step 1: 교재 목차 추출."""
    if os.path.exists(TOC_FILE):
        with open(TOC_FILE, "r", encoding="utf-8") as f:
            toc = json.load(f)
        if toc:
            log.info(f"기존 목차 로드: {len(toc)}개 장")
            return toc

    log.info("=== Step 1: 교재 목차 추출 ===")
    prompt = """이 교재(수목해충학 기본서)의 전체 목차를 알려주세요.

다음 JSON 형식으로 출력해 주세요:
[
  {
    "chapter": 1,
    "title": "장 제목",
    "sections": [
      {"section": "1.1", "title": "절 제목"},
      {"section": "1.2", "title": "절 제목"}
    ]
  },
  ...
]

모든 장과 절을 빠짐없이 포함해 주세요. JSON만 출력하세요."""

    result = query_gemini(prompt)
    if not result:
        log.error("목차 추출 실패")
        return None

    # JSON 파싱
    try:
        # ```json ... ``` 블록 추출
        json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', result, re.DOTALL)
        if json_match:
            toc = json.loads(json_match.group(1))
        else:
            # 직접 파싱 시도
            start = result.find('[')
            end = result.rfind(']') + 1
            toc = json.loads(result[start:end])
    except json.JSONDecodeError as e:
        log.error(f"목차 JSON 파싱 실패: {e}")
        log.info(f"원본 응답:\n{result[:2000]}")
        # 파싱 실패 시 원본 저장
        with open(TOC_FILE.replace('.json', '_raw.txt'), "w", encoding="utf-8") as f:
            f.write(result)
        return None

    with open(TOC_FILE, "w", encoding="utf-8") as f:
        json.dump(toc, f, ensure_ascii=False, indent=2)
    log.info(f"목차 저장: {len(toc)}개 장 → {TOC_FILE}")

    for ch in toc:
        log.info(f"  제{ch['chapter']}장. {ch['title']} ({len(ch.get('sections', []))}개 절)")

    return toc


def step2_classify_questions(toc):
    """Step 2: 175개 문제를 장별로 분류 (Gemini 기본서 활용)."""
    if os.path.exists(CLASSIFICATION_FILE):
        with open(CLASSIFICATION_FILE, "r", encoding="utf-8") as f:
            classification = json.load(f)
        if classification:
            total = sum(len(refs) for refs in classification.values())
            log.info(f"기존 분류 로드: {len(classification)}개 절, {total}개 문제")
            return classification

    log.info("=== Step 2: 문제 분류 ===")
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)
    log.info(f"문제 수: {len(questions)}")

    # 목차 문자열 생성
    toc_text = ""
    for ch in toc:
        toc_text += f"\n제{ch['chapter']}장. {ch['title']}\n"
        for sec in ch.get("sections", []):
            toc_text += f"  {sec['section']} {sec['title']}\n"

    # 25문제씩 배치로 분류 (API 부담 감소)
    classification = {}  # section -> [ref, ...]
    batch_size = 25

    for i in range(0, len(questions), batch_size):
        batch = questions[i:i+batch_size]
        batch_refs = [q["ref"] for q in batch]
        log.info(f"분류 중: {batch_refs[0]} ~ {batch_refs[-1]} ({len(batch)}문제)")

        # 문제 텍스트 준비
        q_text = ""
        for q in batch:
            q_text += f"\n[{q['ref']}] {q['content']}\n"
            for ci in range(1, 6):
                choice = q.get(f"choice{ci}", "")
                if choice:
                    q_text += f"  ①②③④⑤"[ci] + f" {choice}\n"

        prompt = f"""아래는 나무의사 시험 수목해충학 기출문제입니다.
이 교재(수목해충학 기본서)의 목차를 참고하여 각 문제가 어느 절(section)에 해당하는지 분류해 주세요.

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

        # 병합
        for section, refs in batch_cls.items():
            if section not in classification:
                classification[section] = []
            classification[section].extend(refs)

        # API 속도 제한
        time.sleep(2)

    # 분류 결과 저장
    with open(CLASSIFICATION_FILE, "w", encoding="utf-8") as f:
        json.dump(classification, f, ensure_ascii=False, indent=2)

    total = sum(len(refs) for refs in classification.values())
    log.info(f"분류 완료: {len(classification)}개 절, {total}/{len(questions)}개 문제")

    return classification


def step3_generate_chapter(ch_info, classification, questions_by_ref, toc):
    """Step 3: 장별 콘텐츠 생성 (Gemini 기본서 활용)."""
    ch_num = ch_info["chapter"]
    ch_title = ch_info["title"]
    out_path = os.path.join(DATA_DIR, f"entomology_note_ch{ch_num}.md")

    if os.path.exists(out_path):
        with open(out_path, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) > 500:
            log.info(f"  제{ch_num}장 이미 생성됨 ({len(content.splitlines())}줄), 건너뜀")
            return out_path

    sections = ch_info.get("sections", [])

    # 이 장에 해당하는 문제 수집
    ch_prefix = f"{ch_num}."
    ch_questions = []
    ch_section_refs = {}  # section -> [ref, ...]

    for section, refs in classification.items():
        if section.startswith(ch_prefix) or section == str(ch_num):
            ch_section_refs[section] = refs
            for ref in refs:
                if ref in questions_by_ref:
                    ch_questions.append(questions_by_ref[ref])

    log.info(f"  제{ch_num}장. {ch_title}: {len(sections)}개 절, {len(ch_questions)}개 관련 문제")

    # 절별로 나눠서 생성 (절이 많으면 2~3개씩 묶기)
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
        sec_titles = [f"{s['section']} {s['title']}" for s in group]
        log.info(f"    생성 중: {', '.join(sec_numbers)}")

        # 해당 절들의 관련 문제 텍스트
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

        # 관련 문제 ref 정리
        ref_info = ""
        for sec in group:
            sec_num = sec["section"]
            refs = section_ref_map.get(sec_num, [])
            if refs:
                ref_info += f"\n{sec_num}절 관련 문제: {', '.join(f'({r})' for r in refs)}"

        prompt = f"""교재(수목해충학 기본서)를 참고하여 아래 절의 핵심정리 노트를 작성해 주세요.

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
4. 각 절 끝에 관련 문제가 있으면 반드시 **관련 문제**: ({ref_info}의 ref들) 형식으로 추가. ref 형식은 (R-N) 예: (5-26), (7-30).
5. 기출문제에 나온 핵심 내용을 빠짐없이 포함하되, 교재 내용을 바탕으로 더 풍부하게 서술.
6. 화학식은 유니코드 첨자(H₂O, CO₂ 등) 사용, LaTeX 사용 금지.
7. 절 제목(###)에 '핵심 정리' 라벨 붙이지 말 것.
8. 장 제목(##)은 이미 있으므로 작성하지 말 것. 절(###)부터 시작.

노트 마크다운만 출력하세요."""

        result = query_gemini(prompt)
        if result:
            # ## 제N장 제목 줄 제거 (중복 방지)
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

    # 키워드 요약 테이블 생성
    log.info(f"    키워드 요약 테이블 생성 중...")
    summary_prompt = f"""제{ch_num}장 '{ch_title}'의 핵심 키워드 요약 테이블을 작성해 주세요.

이 장에서 다룬 주요 내용(교재 기반)과 관련 기출문제를 고려하여 작성하세요.
관련 기출 문제 ref: {', '.join(f'({r})' for refs in ch_section_refs.values() for r in refs)}

마크다운 테이블 형식으로 출력:
### 핵심 키워드 요약

| 키워드 | 핵심 포인트 |
|--------|------------|
| ... | ... |

15~25개 항목으로 작성. 시험에 자주 출제되는 핵심 내용 위주로.
테이블만 출력하세요."""

    summary_result = query_gemini(summary_prompt)
    if summary_result:
        # ```블록 제거
        summary_lines = summary_result.split('\n')
        summary_filtered = [l for l in summary_lines if not l.strip().startswith("```")]
        chapter_parts.append('\n'.join(summary_filtered).strip())

    # 파일 저장
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


def main():
    log.info("===== 수목해충학 쪽집게 노트 생성 시작 =====")

    # 문제 로드
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)
    log.info(f"문제 로드: {len(questions)}개")
    questions_by_ref = {q["ref"]: q for q in questions}

    # Step 1: 목차 추출
    toc = step1_get_toc()
    if not toc:
        log.error("목차 추출 실패, 종료")
        return

    # Step 2: 문제 분류
    classification = step2_classify_questions(toc)
    if not classification:
        log.error("문제 분류 실패, 종료")
        return

    # Step 3: 장별 콘텐츠 생성
    log.info(f"=== Step 3: 장별 콘텐츠 생성 ({len(toc)}개 장) ===")
    for ch_info in toc:
        step3_generate_chapter(ch_info, classification, questions_by_ref, toc)
        time.sleep(2)

    # Step 4: 커버리지 검증
    missing = step4_verify_coverage(classification, questions)

    # 결과 요약
    log.info("===== 완료 =====")
    md_files = sorted(
        [f for f in os.listdir(DATA_DIR) if f.startswith("entomology_note_ch") and f.endswith(".md")]
    )
    for f in md_files:
        path = os.path.join(DATA_DIR, f)
        with open(path, "r", encoding="utf-8") as fh:
            lines = len(fh.readlines())
        log.info(f"  {f}: {lines}줄")

    log.info(f"\n다음 단계: python save_study_note.py (수목해충학 모드)")


if __name__ == "__main__":
    main()
