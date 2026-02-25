"""
쪽집게 노트 마크다운 파서.
knou_agriculture/main/views.py의 parse_note_chapters()를 포팅.
ref 형식: (R-N) where R=회차, N=문제번호
"""
import re

_note_chapters_cache = {}


def parse_note_chapters(content, subject_pk, cache_version=None):
    """StudyNote 마크다운을 장/절/항 구조로 파싱.
    ref 형식: (R-N) — R=회차(5~11), N=문제번호(1~25).
    """
    cache_key = f"note_{subject_pk}"
    if cache_version is not None:
        cached = _note_chapters_cache.get(cache_key)
        if cached and cached[0] == cache_version:
            return cached[1]

    chapters = []
    current_chapter = None
    current_section = None
    current_subsection = None
    content_lines = []

    def _flush_content():
        nonlocal content_lines
        if not content_lines:
            return
        text = "\n".join(content_lines).strip()
        if not text:
            content_lines = []
            return

        # 관련 문제 추출: (R-N) 형식 (R=회차 1~2자리, N=문제번호)
        questions = re.findall(r"(?<!\w)(\d{1,2}-\d+)(?!\w)", text)

        # 관련 문제 줄 제거
        body = re.sub(r"\*\*관련 문제\*\*:.*", "", text, flags=re.DOTALL).strip()
        body = re.sub(r"\*\*관련 기출문제\*\*.*", "", body, flags=re.DOTALL).strip()
        body = re.sub(r"\*\*핵심 정리\*\*", "", body)

        html_lines = []
        table_rows = []
        para_lines = []

        def _flush_table():
            nonlocal table_rows
            if not table_rows:
                return
            html_lines.append("<table class='tb-summary'>")
            for idx, row in enumerate(table_rows):
                tag = "th" if idx == 0 else "td"
                cells = [c.strip() for c in row.strip("|").split("|")]
                cells_html = "".join(f"<{tag}>{c}</{tag}>" for c in cells)
                html_lines.append(f"<tr>{cells_html}</tr>")
            html_lines.append("</table>")
            table_rows = []

        def _flush_para():
            nonlocal para_lines
            if not para_lines:
                return
            joined = " ".join(para_lines)
            joined = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", joined)
            joined = re.sub(r"\*(.+?)\*", r"<em>\1</em>", joined)
            html_lines.append(f"<p>{joined}</p>")
            para_lines = []

        for line in body.split("\n"):
            line = line.strip()
            if not line:
                _flush_table()
                _flush_para()
                continue
            if line.startswith("|"):
                _flush_para()
                if re.match(r"^\|[\s\-:|]+\|$", line):
                    continue
                line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
                line = re.sub(r"\*(.+?)\*", r"<em>\1</em>", line)
                table_rows.append(line)
                continue
            _flush_table()
            circled = re.match(r"^([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳])\s*(.*)", line)
            if circled:
                _flush_para()
                num, lc = circled.group(1), circled.group(2)
                lc = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", lc)
                lc = re.sub(r"\*(.+?)\*", r"<em>\1</em>", lc)
                html_lines.append(f"<div class='num-item'><span class='num-marker'>{num}</span>{lc}</div>")
            elif line.startswith("→ ") or line.startswith("  → "):
                _flush_para()
                lc = line.lstrip().lstrip("→").strip()
                lc = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", lc)
                lc = re.sub(r"\*(.+?)\*", r"<em>\1</em>", lc)
                html_lines.append(f"<div class='num-item num-sub'>→ {lc}</div>")
            elif line.startswith("- "):
                _flush_para()
                lc = line[2:]
                lc = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", lc)
                lc = re.sub(r"\*(.+?)\*", r"<em>\1</em>", lc)
                html_lines.append(f"<li>{lc}</li>")
            elif line.startswith("  - "):
                _flush_para()
                lc = line[4:]
                lc = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", lc)
                lc = re.sub(r"\*(.+?)\*", r"<em>\1</em>", lc)
                html_lines.append(f"<li class='sub-item'>{lc}</li>")
            else:
                para_lines.append(line)

        _flush_table()
        _flush_para()

        has_li = any("<li>" in h or "<li " in h for h in html_lines)
        has_table = any("<table" in h for h in html_lines)
        if has_li and not has_table:
            content_html = "<ul>" + "".join(html_lines) + "</ul>"
        elif has_li and has_table:
            parts = []
            li_buf = []
            for h in html_lines:
                if h.startswith("<li"):
                    li_buf.append(h)
                else:
                    if li_buf:
                        parts.append("<ul>" + "".join(li_buf) + "</ul>")
                        li_buf = []
                    parts.append(h)
            if li_buf:
                parts.append("<ul>" + "".join(li_buf) + "</ul>")
            content_html = "".join(parts)
        else:
            content_html = "".join(html_lines)

        target = current_subsection or current_section
        if target:
            target["content_html"] = content_html
            target["questions"] = questions
        content_lines = []

    for line in content.split("\n"):
        m = re.match(r"^## (제\d+장\..+|부록.+)", line)
        if m:
            _flush_content()
            current_chapter = {
                "id": f"ch{len(chapters)+1}",
                "title": m.group(1).strip(),
                "sections": [],
            }
            chapters.append(current_chapter)
            current_section = None
            current_subsection = None
            continue

        m = re.match(r"^### (.+)", line)
        if m and current_chapter is not None:
            _flush_content()
            sec_title = m.group(1).strip()
            current_section = {
                "id": f"{current_chapter['id']}-s{len(current_chapter['sections'])+1}",
                "title": sec_title,
                "content_html": "",
                "questions": [],
                "subsections": [],
            }
            current_chapter["sections"].append(current_section)
            current_subsection = None
            continue

        m = re.match(r"^#### (.+)", line)
        if m and current_section is not None:
            _flush_content()
            sub_title = m.group(1).strip()
            current_subsection = {
                "id": f"{current_section['id']}-sub{len(current_section['subsections'])+1}",
                "title": sub_title,
                "content_html": "",
                "questions": [],
            }
            current_section["subsections"].append(current_subsection)
            continue

        if line.startswith("# ") or line.startswith("---") or line.startswith("> "):
            continue
        content_lines.append(line)

    _flush_content()

    # total_questions 계산
    for ch in chapters:
        for sec in ch["sections"]:
            seen = set()
            unique_q = []
            for q in sec["questions"]:
                if q not in seen:
                    seen.add(q)
                    unique_q.append(q)
            for sub in sec["subsections"]:
                for q in sub["questions"]:
                    if q not in seen:
                        seen.add(q)
                        unique_q.append(q)
            sec["total_questions"] = len(unique_q)
            sec["all_questions"] = unique_q

    if cache_version is not None:
        _note_chapters_cache[cache_key] = (cache_version, chapters)
    return chapters
