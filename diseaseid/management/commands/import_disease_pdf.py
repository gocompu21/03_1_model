"""병해 식별 학습 PDF를 병해 암기 데이터로 임포트.

'2026 병해 식별 공부' 형식의 PDF를 읽어 DiseaseCourse / DiseaseQuestion 으로 적재한다.

PDF 구조 (전제):
    - 종별 상세 페이지: 사진 여러 장 + 분류/학명/기주/설명 + 종 번호
      (종 번호는 페이지 텍스트에 홀로 있는 숫자. 예: "01", "26", "153")
      번호가 없는 페이지는 직전 종의 추가 사진 페이지로 간주한다.
    - 분류군별 요약표: "(기주) 병명 추가사항 비고" 헤더 아래
      "026 잣나무 털녹병 중간기주: 송이풀 기출★★" 형태의 행.
    - 맨 뒤 가나다순 목록: 정확한 병명 153종. 요약표 행에서 기주와 병명의
      경계를 가르는 기준으로 쓴다.

사진에 인코딩된 글씨(표징 설명, 화살표)는 그대로 두되, PDF 본문의 정답
텍스트가 노출되지 않도록 페이지 렌더링이 아니라 사진만 추출해 합성한다.

사용 예:
    python manage.py import_disease_pdf "2026 병해 식별공부.pdf" --dry-run
    python manage.py import_disease_pdf "2026 병해 식별공부.pdf"
    python manage.py import_disease_pdf "..." --replace
"""

import hashlib
import io
import re

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from diseaseid.models import DiseaseCourse, DiseaseQuestion

SUMMARY_HEADER_RE = re.compile(r"\(?기주\)?\s*병\s*명|병\s*명\s*추가")
SUMMARY_ROW_RE = re.compile(r"^(\d{3})\s+(.*)$")
NOTE_RE = re.compile(r"\s*기출\s*([★☆*]*)\s*$")

# 가나다순 목록 페이지 판별
INDEX_HEADER = "수록 병해"

# 기출 표기: "기출★★ [8회(병명)] [10회(...)]"
EXAM_RE = re.compile(r"기출\s*([★☆]*)")
EXAM_ROUND_RE = re.compile(r"\[\s*(\d+\s*회[^\[\]\n]*)", re.M)

# 상세 페이지의 라벨
HOST_RE = re.compile(r"\*?\s*기주\s*:\s*([^*\n]+)")
ALT_HOST_RE = re.compile(r"중간기주\s*:\s*([^*\n]+)")
# 분류: "진균계. 담자균문. 떡병균과(Exobasidiaceae)."
TAXONOMY_RE = re.compile(r"((?:진균계|난균계|세균|파이토플라스마|바이러스|조류|선충)[^\n]*?)(?=\s*\*|\s*$)", re.M)
# 학명: 이탤릭이 텍스트로는 구분되지 않아 라틴 문자 덩어리로 잡는다
LATIN_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+(?:spp?\.|[a-z-]+))(?:\s+(?:var|f|subsp)\.\s*[a-z-]+)?)")

# 이미지 합성 설정
MAX_PHOTOS = 6
MIN_PHOTO_AREA = 20000
SHEET_WIDTH = 1000
CELL_GAP = 8
SINGLE_COLUMN_MAX = 3


class Command(BaseCommand):
    help = "병해 식별 학습 PDF를 병해 암기 코스로 임포트한다"

    def add_arguments(self, parser):
        parser.add_argument("pdf_file", help="PDF 파일 경로")
        parser.add_argument("--prefix", default="병해식별", help="코스명 접두어")
        parser.add_argument("--replace", action="store_true", help="기존 문제를 지우고 새로 넣는다")
        parser.add_argument("--dry-run", action="store_true", help="DB에 쓰지 않고 결과만 출력")
        parser.add_argument("--limit", type=int, default=0, help="앞에서 N종만 처리")

    def handle(self, *args, **opts):
        try:
            from pypdf import PdfReader
        except ImportError:
            raise CommandError("pypdf가 필요합니다: pip install pypdf")

        try:
            reader = PdfReader(opts["pdf_file"])
        except FileNotFoundError:
            raise CommandError(f"파일을 찾을 수 없습니다: {opts['pdf_file']}")

        pages = [(p, p.extract_text() or "") for p in reader.pages]
        self.stdout.write(f"페이지 {len(pages)}개")

        known_names = self._parse_name_index(pages)
        self.stdout.write(f"가나다순 목록에서 병명 {len(known_names)}개 수집")

        summary, groups = self._parse_summaries(pages, known_names)
        self.stdout.write(f"요약표에서 {len(summary)}종 / 분류군 {len(groups)}개 수집")

        items = self._parse_details(pages, summary)
        self.stdout.write(f"상세 페이지에서 {len(items)}종 파싱")

        if opts["limit"]:
            items = items[: opts["limit"]]

        if opts["dry_run"]:
            self._report(items, groups)
            return

        self._save(items, groups, opts)

    # ------------------------------------------------------------------ 파싱

    def _parse_name_index(self, pages):
        """맨 뒤 가나다순 목록에서 정확한 병명들을 모은다."""
        names = []
        started = False
        for _, text in pages:
            if INDEX_HEADER in text:
                started = True
            if not started:
                continue
            for line in text.split("\n"):
                line = line.strip()
                if not line or INDEX_HEADER in line:
                    continue
                if re.match(r"^[가-힣A-Za-z(]", line) and len(line) <= 30:
                    names.append(line)
        # 긴 이름부터 맞춰야 '떡병'이 '민떡병'을 가로채지 않는다
        return sorted(set(names), key=len, reverse=True)

    def _parse_summaries(self, pages, known_names):
        """요약표에서 번호별 기주/병명/추가사항/기출을, 분류군 구간을 수집."""
        summary = {}
        groups = []

        for _, text in pages:
            lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
            if not any(SUMMARY_HEADER_RE.search(ln) for ln in lines):
                continue

            title_parts, numbers = [], []
            for ln in lines:
                m = SUMMARY_ROW_RE.match(ln)
                if m:
                    no = int(m.group(1))
                    row = self._parse_summary_row(m.group(2), known_names)
                    if row["name"]:
                        summary[no] = row
                        numbers.append(no)
                elif not SUMMARY_HEADER_RE.search(ln):
                    title_parts.append(ln)

            if numbers:
                groups.append({
                    "title": " ".join(" ".join(title_parts).split()),
                    "numbers": numbers,
                })

        return summary, groups

    def _parse_summary_row(self, rest, known_names):
        """'잣나무 털녹병 중간기주: 송이풀 기출★★' 을 항목별로 나눈다."""
        note_m = NOTE_RE.search(rest)
        stars = len(note_m.group(1)) if note_m else 0
        body = NOTE_RE.sub("", rest).strip()

        # 여러 병을 한 줄에 나열한 비교 설명행은 종이 아니다
        if "①" in body or body.count("병") > 2 and "②" in body:
            return {"name": "", "host": "", "note": "", "alt_host": "", "stars": 0}
        # 'ㅇㅇ: ㅇㅇ' 형태의 설명행(예: '유성세대 전염원: 자낭포자')
        if ":" in body and not any(body.startswith(n[:2]) for n in known_names):
            head_word = body.split(":")[0].strip()
            if not any(head_word.endswith(x) for x in ("병", "부후", "버섯")):
                return {"name": "", "host": "", "note": "", "alt_host": "", "stars": 0}

        # 가나다순 목록에 있는 병명을 찾는다. 목록 이름 자체가 '기주 + 병명'인
        # 경우가 많아(예: '잣나무 털녹병') 먼저 그대로 맞춰본다.
        name, extra = "", ""
        for known in known_names:
            idx = body.find(known)
            if idx != -1:
                name = known
                extra = body[idx + len(known):].strip()
                break

        if not name:
            name = re.sub(r"[()]", "", body).strip()

        m = ALT_HOST_RE.search(extra)
        alt_host = self._clean(m.group(1)) if m else ""
        if alt_host:
            extra = ALT_HOST_RE.sub("", extra).strip()

        return {
            "name": name,
            # 요약표의 병명은 대개 기주를 품고 있어 따로 떼지 않는다.
            # 기주는 상세 페이지의 '기주:' 라벨에서 채운다.
            "host": "",
            "note": self._clean(extra),
            "alt_host": alt_host,
            "stars": stars,
        }

    def _parse_details(self, pages, summary):
        """상세 페이지를 종 단위로 묶어 사진과 참고 정보를 모은다."""
        items = []
        pending = []
        expected = 1
        last = max(summary) if summary else 0
        started = False

        for page, text in pages:
            if any(SUMMARY_HEADER_RE.search(ln) for ln in text.split("\n")):
                pending = []
                continue
            if INDEX_HEADER in text:
                break

            if not started:
                if not HOST_RE.search(text) and not TAXONOMY_RE.search(text):
                    continue
                started = True

            pending.append((page, text))

            if expected > last or not self._has_number(text, expected):
                continue

            detail = {"host": "", "taxonomy": "", "pathogen": "", "alt_host": ""}
            exam = (0, "")
            for _, tx in pending:
                got = self._parse_detail_fields(tx)
                for k, v in got.items():
                    if v and not detail.get(k):
                        detail[k] = v
                if not exam[0]:
                    exam = self._parse_exam(tx)

            row = summary.get(expected, {})
            items.append({
                "no": expected,
                "name": row.get("name", ""),
                # 기주는 상세 페이지가 더 자세하다
                "host": detail["host"] or row.get("host", ""),
                "pathogen": detail["pathogen"],
                "note": row.get("note", ""),
                "taxonomy": detail["taxonomy"],
                "alt_host": detail["alt_host"] or row.get("alt_host", ""),
                "exam_stars": exam[0] or row.get("stars", 0),
                "exam_note": exam[1],
                "pages": [p for p, _ in pending],
            })
            pending = []
            expected += 1

        return items

    def _parse_detail_fields(self, text):
        """상세 페이지에서 기주/분류/학명/중간기주를 뽑는다."""
        out = {}

        m = HOST_RE.search(text)
        if m:
            out["host"] = self._clean(m.group(1))

        m = ALT_HOST_RE.search(text)
        if m:
            out["alt_host"] = self._clean(m.group(1))

        for line in text.split("\n"):
            if re.search(r"진균계|난균계|세균|파이토플라스마|바이러스|조류|선충", line):
                taxo = re.sub(r"기출.*?\]", "", line)
                taxo = re.sub(r"[*]", " ", taxo)
                # 학명(라틴어)은 분류에서 떼어 병원균으로
                latin = LATIN_RE.search(taxo)
                if latin:
                    out.setdefault("pathogen", latin.group(1).strip())
                    taxo = taxo.replace(latin.group(1), " ")
                taxo = re.sub(r"\s+", " ", taxo).strip(" .,")
                if taxo:
                    out.setdefault("taxonomy", taxo[:200])
                break

        if "pathogen" not in out:
            latin = LATIN_RE.search(text)
            if latin:
                out["pathogen"] = latin.group(1).strip()

        return out

    def _parse_exam(self, text):
        """기출 표기에서 (별 개수, '8회 (병명) · 10회') 를 만든다."""
        m = EXAM_RE.search(text)
        if not m or not m.group(1):
            return 0, ""

        line = text[: m.end()].split("\n")[-1] + text[m.end():].split("\n")[0]
        rounds = []
        for raw in EXAM_ROUND_RE.findall(line):
            label = re.sub(r"\s+", "", raw).replace("(", " (")
            if len(label) > 30:
                label = re.match(r"\d+회", label).group(0)
            if label and label not in rounds:
                rounds.append(label)

        return len(m.group(1)), " · ".join(rounds)

    @staticmethod
    def _has_number(text, n):
        tokens = re.findall(r"(?<![\d~\-.])\d{1,3}(?![\d~\-.회장쌍령년월일%])", text)
        return f"{n:02d}" in tokens or str(n) in tokens

    @staticmethod
    def _clean(value):
        value = (value or "").strip()
        value = re.sub(r"[©ⓒ].*$", "", value)
        value = re.sub(r"\s*기출\s*[★☆]*\s*$", "", value)
        value = re.sub(r"\s+\d{1,3}\s*$", "", value)
        value = re.sub(r"\s+", " ", value).strip(" .,·*")
        return value[:280]

    # ------------------------------------------------------------------ 이미지

    def _build_image(self, item):
        """종의 사진들을 한 장으로 합성. 사진 안의 글씨는 그대로 둔다."""
        from PIL import Image

        photos = []
        for page in item["pages"]:
            for embedded in page.images:
                try:
                    img = Image.open(io.BytesIO(embedded.data))
                    img.load()
                except Exception:
                    continue
                if img.width * img.height < MIN_PHOTO_AREA:
                    continue
                photos.append(img.convert("RGB"))

        if not photos:
            return None

        photos = photos[:MAX_PHOTOS]
        cols = 1 if len(photos) <= SINGLE_COLUMN_MAX else 2
        rows = (len(photos) + cols - 1) // cols
        cell_w = (SHEET_WIDTH - CELL_GAP * (cols + 1)) // cols
        cell_h = int(cell_w * (0.72 if cols == 1 else 0.75))

        for photo in photos:
            photo.thumbnail((cell_w, cell_h), Image.LANCZOS)
        row_heights = [
            max(p.height for p in photos[r * cols:(r + 1) * cols]) for r in range(rows)
        ]

        sheet = Image.new(
            "RGB", (SHEET_WIDTH, CELL_GAP + sum(h + CELL_GAP for h in row_heights)),
            (255, 255, 255),
        )
        y = CELL_GAP
        for r in range(rows):
            for c, photo in enumerate(photos[r * cols:(r + 1) * cols]):
                x = CELL_GAP + c * (cell_w + CELL_GAP) + (cell_w - photo.width) // 2
                sheet.paste(photo, (x, y + (row_heights[r] - photo.height) // 2))
            y += row_heights[r] + CELL_GAP

        buffer = io.BytesIO()
        sheet.save(buffer, format="JPEG", quality=80, optimize=True, progressive=True)
        return buffer.getvalue()

    # ------------------------------------------------------------------ 출력

    def _report(self, items, groups):
        self.stdout.write(self.style.WARNING("[dry-run] DB에 쓰지 않습니다."))
        for g in groups:
            self.stdout.write(f"\n■ {g['title']} ({len(g['numbers'])}종)")

        self.stdout.write("")
        for it in items[:10]:
            self.stdout.write(
                f"  {it['no']:>3} {it['name'][:20]:<22} 기주={it['host'][:18]:<20} "
                f"병원균={it['pathogen'][:24]:<26} {'★' * it['exam_stars']}"
            )
        self.stdout.write(f"\n총 {len(items)}종")
        for key in ("name", "host", "pathogen", "note", "taxonomy"):
            filled = sum(1 for it in items if it.get(key))
            self.stdout.write(f"  {key}: {filled}/{len(items)}종")
        self.stdout.write(f"  기출: {sum(1 for it in items if it['exam_stars'])}종")

    # ------------------------------------------------------------------ 저장

    @transaction.atomic
    def _save(self, items, groups, opts):
        by_no = {it["no"]: it for it in items}
        prefix = opts["prefix"]
        total_added = 0

        for order, group in enumerate(groups, 1):
            members = [by_no[n] for n in group["numbers"] if n in by_no]
            if not members:
                continue

            name = f"{prefix} {order:02d}. {self._short_title(group['title'])}"
            course, created = DiseaseCourse.objects.get_or_create(
                name=name, defaults={"description": group["title"][:200], "order": order},
            )
            if not created:
                course.description = group["title"][:200]
                course.order = order
                course.save(update_fields=["description", "order"])

            if opts["replace"]:
                course.questions.all().delete()

            existing = set(course.questions.values_list("source_key", flat=True))
            added = 0

            for item in members:
                key = f"pdf-{item['no']:03d}"
                if key in existing:
                    continue

                blob = self._build_image(item)
                if not blob:
                    self.stderr.write(f"  [{item['no']}] 사진이 없어 건너뜀")
                    continue

                q = DiseaseQuestion(
                    course=course,
                    order=item["no"],
                    source_key=key,
                    name=item["name"],
                    host=item["host"],
                    pathogen=item["pathogen"],
                    note=item["note"],
                    taxonomy=item["taxonomy"],
                    alt_host=item["alt_host"],
                    exam_stars=item["exam_stars"],
                    exam_note=item["exam_note"],
                )
                digest = hashlib.sha256(blob).hexdigest()[:12]
                q.image.save(f"dis_{item['no']:03d}_{digest}.jpg", ContentFile(blob), save=False)
                q.save()
                added += 1

            total_added += added
            self.stdout.write(f"  {course.name}: +{added}종 (총 {course.questions.count()})")

        self.stdout.write(self.style.SUCCESS(f"완료: 문제 {total_added}개 추가"))

    @staticmethod
    def _short_title(title):
        title = re.sub(r"^진균계\s*", "", title)
        # 표 아래 설명이 제목으로 딸려 오는 경우를 잘라낸다
        title = re.split(r"[①②③④]|기출", title)[0]
        parts = [p.strip() for p in re.split(r"[,·]", title) if p.strip()]
        if len(parts) > 2:
            return f"{parts[0]} 외 {len(parts) - 1}"
        return " ".join(title.split())[:60]
