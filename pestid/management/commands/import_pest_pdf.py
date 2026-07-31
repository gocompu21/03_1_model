"""해충 식별 학습 PDF를 해충 식별 퀴즈 데이터로 임포트.

'2026 해충 식별 공부' 형식의 PDF를 읽어 PestCourse / PestQuestion 으로 적재한다.

PDF 구조 (전제):
    - 종별 상세 페이지: 사진 여러 장 + 분류/기주/여름기주/연 발생횟수/월동태 + 종 번호
      (종 번호는 페이지 텍스트에 홀로 있는 숫자. 예: "01", "17", "176")
      번호가 없는 페이지는 직전 종의 추가 사진 페이지로 간주한다.
    - 분류군별 요약표 페이지: "해충명 연 발생횟수 월동태 비고" 헤더 아래
      "001 붉나무혹응애 수회 미확인 기출 ★" 형태의 행. 해충명은 여기서만 얻는다.

각 종의 사진들을 한 장으로 합쳐 문제 이미지로 쓴다. 상세 페이지의 텍스트에는
정답(연 발생횟수/월동태 등)이 그대로 적혀 있으므로 페이지 렌더링이 아니라
사진만 추출해 합성한다.

사용 예:
    python manage.py import_pest_pdf "2026 해충식별공부.pdf" --dry-run
    python manage.py import_pest_pdf "2026 해충식별공부.pdf" --prefix "해충식별"
    python manage.py import_pest_pdf "2026 해충식별공부.pdf" --replace
"""

import hashlib
import io
import re

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from pestid.models import PestCourse, PestQuestion

# 상세 페이지에서 뽑아낼 라벨 -> 모델 필드
DETAIL_LABELS = [
    ("여름기주", "host"),
    ("겨울기주", None),
    ("기주", None),
    ("연 발생횟수", "occurrence"),
    ("월동태", "overwinter"),
    ("월동처", None),
]
LABEL_RE = re.compile(r"(여름기주|겨울기주|기주|연\s*발생횟수|월동태|월동처)\s*:")

# 상세 페이지의 분류 표기. 예: "거미강 응애목 혹응애과", "메뚜기목 여치과"
# 강(綱)은 있을 때도 없을 때도 있어 목/과만 취한다. 속(屬)은 PDF에 없다.
TAXON_RE = re.compile(r"(?:^|\s)(\S*?목)\s+(\S*?(?:과|상과))(?=\s|$|,)")

SUMMARY_HEADER = "해충명"
SUMMARY_ROW_RE = re.compile(r"^(\d{3})\s+(\S+)\s+(.*)$")
NOTE_RE = re.compile(r"\s*기출\s*([★☆*]*)\s*$")

# 요약표의 '연 발생횟수' 열. 이 뒤에 남는 부분이 '월동태' 열이다.
# 예: "1회", "2~3회", "보통 1회", "2년에 1회", "6년 1회", "1~2년에 1회",
#     "수회(7~8회)", "7회 이상", "남부2회,중부1회", "1회,2년에 1회"
_COUNT = r"(?:\d+\s*[~-]?\s*\d*\s*년에?\s*)?\d+\s*[~-]?\s*\d*\s*회(?:\s*이상)?(?:\([^)]*\))?"
OCCURRENCE_RE = re.compile(
    rf"^(?:(?:주로|보통|약|남부|중부)\s*)?{_COUNT}"
    rf"(?:\s*,\s*(?:(?:주로|보통|남부|중부)\s*)?{_COUNT})*"
    r"|^(?:수회(?:\([^)]*\))?|미확인|불명)"
)

# 이미지 합성 설정
MAX_PHOTOS = 6
MIN_PHOTO_AREA = 20000  # 이보다 작으면 아이콘/장식으로 보고 버린다
SHEET_WIDTH = 1000
CELL_GAP = 8
# 원본 사진 폭의 중앙값이 약 720px이라 2열로 깔면 사진이 절반으로 줄어든다.
# 사진이 이 수 이하면 세로로 쌓아 한 장을 최대한 크게 보여준다.
SINGLE_COLUMN_MAX = 3


class Command(BaseCommand):
    help = "해충 식별 학습 PDF를 퀴즈 코스로 임포트한다"

    def add_arguments(self, parser):
        parser.add_argument("pdf_file", help="PDF 파일 경로")
        parser.add_argument(
            "--prefix", default="해충식별", help="코스명 앞에 붙일 접두어 (기본: 해충식별)"
        )
        parser.add_argument(
            "--replace", action="store_true", help="같은 이름의 코스 문제를 지우고 새로 넣는다"
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="DB에 쓰지 않고 파싱 결과만 출력한다"
        )
        parser.add_argument(
            "--limit", type=int, default=0, help="앞에서 N종만 처리 (테스트용)"
        )

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

        summary, groups = self._parse_summaries(pages)
        self.stdout.write(f"요약표에서 해충명 {len(summary)}개 / 분류군 {len(groups)}개 수집")

        items = self._parse_details(pages, summary)
        self.stdout.write(f"상세 페이지에서 {len(items)}종 파싱")

        missing = sorted(set(summary) - {it["no"] for it in items})
        if missing:
            self.stderr.write(
                self.style.WARNING(f"상세 페이지를 못 찾은 번호 {len(missing)}개: {missing[:20]}")
            )

        if opts["limit"]:
            items = items[: opts["limit"]]

        if opts["dry_run"]:
            self._report(items, groups)
            return

        self._save(items, groups, opts)

    # ------------------------------------------------------------------ 파싱

    def _parse_summaries(self, pages):
        """요약표에서 번호별 해충명/연발생횟수/월동태/기출표시와 분류군 구간을 수집."""
        summary = {}
        groups = []  # [{"title":..., "numbers":[...]}]

        for _, text in pages:
            lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
            if not any(SUMMARY_HEADER in ln and "월동태" in ln for ln in lines):
                continue

            title_parts, numbers = [], []
            for ln in lines:
                m = SUMMARY_ROW_RE.match(ln)
                if m:
                    no = int(m.group(1))
                    summary[no] = self._parse_summary_row(m)
                    numbers.append(no)
                elif SUMMARY_HEADER not in ln:
                    title_parts.append(ln)

            if numbers:
                groups.append(
                    {
                        "title": " ".join(" ".join(title_parts).split()),
                        "numbers": numbers,
                    }
                )

        return summary, groups

    def _parse_summary_row(self, match):
        """'001 붉나무혹응애 수회 미확인 기출 ★' 한 줄을 항목별로 나눈다."""
        note = NOTE_RE.search(match.group(3))
        rest = NOTE_RE.sub("", match.group(3)).strip()

        occurrence = overwinter = ""
        m = OCCURRENCE_RE.match(rest)
        if m:
            occurrence = m.group(0).strip()
            overwinter = rest[m.end() :].strip()
        else:
            overwinter = rest

        return {
            "name": match.group(2),
            "occurrence": self._clean(occurrence),
            "overwinter": self._clean(overwinter),
            "is_past": bool(note),
            "stars": len(note.group(1)) if note else 0,
        }

    def _parse_details(self, pages, summary):
        """상세 페이지를 종 단위로 묶어 정답 항목과 사진을 모은다."""
        items = []
        pending = []  # 아직 번호를 만나지 못한 페이지들 (앞선 추가 사진 페이지)
        expected = 1
        last = max(summary) if summary else 0
        started = False  # 첫 상세 페이지 전의 표지/출처 페이지를 버리기 위한 플래그

        for page, text in pages:
            if SUMMARY_HEADER in text and "월동태" in text and "비고" in text:
                pending = []  # 요약표는 어느 종에도 속하지 않는다
                continue

            if not started:
                if not LABEL_RE.search(text):
                    continue
                started = True

            pending.append((page, text))

            if expected > last or not self._has_number(text, expected):
                continue

            detail = {}
            taxon = ("", "")
            for _, tx in pending:
                for key, value in self._parse_fields(tx).items():
                    detail.setdefault(key, value)
                if not taxon[0]:
                    taxon = self._parse_taxon(tx)

            row = summary.get(expected, {})
            items.append(
                {
                    "no": expected,
                    "name": row.get("name", ""),
                    "is_past": row.get("is_past", False),
                    "stars": row.get("stars", 0),
                    # 요약표 표기를 대표 정답으로, 상세 페이지 표기를 별해로 인정한다
                    "occurrence": self._merge(
                        row.get("occurrence", ""), detail.get("occurrence", "")
                    ),
                    "overwinter": self._merge(
                        row.get("overwinter", ""), detail.get("overwinter", "")
                    ),
                    "host": detail.get("host", ""),
                    "taxon_order": taxon[0],
                    "taxon_family": taxon[1],
                    "pages": [p for p, _ in pending],
                }
            )
            pending = []
            expected += 1

        return items

    @staticmethod
    def _parse_taxon(text):
        """상세 페이지 분류 표기에서 (목, 과)를 뽑는다. 없으면 빈 문자열."""
        for line in text.split("\n"):
            # 기출 표시의 괄호 주석에도 '월동태:' 같은 라벨이 들어 있어 먼저 지운다
            # 예: "기출★★ [4회(월동태: 약충)] [9회]   노린재목 가루깍지벌레과"
            cleaned = re.sub(r"\[[^\]]*\]", " ", line)
            head = LABEL_RE.split(cleaned)[0]
            m = TAXON_RE.search(head)
            if m:
                return m.group(1), m.group(2)
        return "", ""

    @staticmethod
    def _has_number(text, n):
        """페이지 텍스트에 종 번호가 홀로 적혀 있는지."""
        tokens = re.findall(r"(?<![\d~\-.])\d{1,3}(?![\d~\-.회장쌍령년월일%])", text)
        return f"{n:02d}" in tokens or str(n) in tokens

    def _parse_fields(self, text):
        """'기주: ...   연 발생횟수: ...   월동태: ...' 형태에서 값을 뽑는다."""
        result = {}

        for line in text.split("\n"):
            matches = list(LABEL_RE.finditer(line))
            for i, m in enumerate(matches):
                label = re.sub(r"\s+", " ", m.group(1))
                end = matches[i + 1].start() if i + 1 < len(matches) else len(line)
                value = self._clean(line[m.end() : end])

                field = dict(DETAIL_LABELS).get(label)
                if field and value and field not in result:
                    result[field] = value

        return result

    @staticmethod
    def _merge(primary, alternate):
        """요약표 표기를 대표 정답으로, 나머지 표기를 별해로 이어 붙인다.

        모델은 쉼표를 별해 구분자로 쓰고 첫 값을 대표 정답으로 보여주므로,
        '3령약충,성충'처럼 원래 한 덩어리인 값의 쉼표는 '또는'으로 바꿔
        대표 정답이 잘리지 않게 하고, 낱개 표기는 뒤에 별해로 덧붙인다.
        """
        values = []

        def add(value, drop_similar=False):
            value = value.strip(" ,")
            if not value:
                return
            squashed = value.replace(" ", "")
            for existing in (v.replace(" ", "") for v in values):
                if squashed == existing:
                    return
                if drop_similar and (
                    squashed.startswith(existing) or existing.startswith(squashed)
                ):
                    return
            values.append(value)

        sources = [v.strip() for v in (primary, alternate) if v and v.strip()]

        for i, source in enumerate(sources):
            add(re.sub(r"\s*,\s*", " 또는 ", source), drop_similar=i > 0)
        for source in sources:  # 낱개 표기도 정답으로 인정
            for part in source.split(","):
                add(part)

        return ", ".join(values)

    @staticmethod
    def _clean(value):
        """값 뒤에 붙은 페이지 번호, 각주, 출처 표기를 털어낸다."""
        value = value.strip().split("*")[0]
        value = re.sub(r"[©ⓒ].*$", "", value)
        value = re.split(r"\s{2,}", value.strip())[0]  # 같은 줄 뒤쪽의 설명문 분리
        value = re.sub(r"\([^)]*\)", "", value)  # 괄호 주석 제거
        value = re.sub(r"\s+\d{1,3}\s*$", "", value)  # 꼬리에 붙은 종 번호
        value = re.sub(r"(?<=\d)\s*-\s*(?=\d)", "~", value)  # 5-6회 -> 5~6회
        value = re.sub(r"\s+", " ", value).strip(" .,·")
        return value

    # ------------------------------------------------------------------ 이미지

    def _build_image(self, item):
        """종의 사진들을 한 장으로 합성. 실패하면 None."""
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

        # 각 사진을 셀에 맞춰 축소한 뒤, 실제로 쓰인 높이만큼만 시트를 잡는다
        for photo in photos:
            photo.thumbnail((cell_w, cell_h), Image.LANCZOS)
        row_heights = [
            max(p.height for p in photos[r * cols : (r + 1) * cols]) for r in range(rows)
        ]

        sheet = Image.new(
            "RGB",
            (SHEET_WIDTH, CELL_GAP + sum(h + CELL_GAP for h in row_heights)),
            (255, 255, 255),
        )

        y = CELL_GAP
        for r in range(rows):
            for c, photo in enumerate(photos[r * cols : (r + 1) * cols]):
                x = CELL_GAP + c * (cell_w + CELL_GAP) + (cell_w - photo.width) // 2
                sheet.paste(photo, (x, y + (row_heights[r] - photo.height) // 2))
            y += row_heights[r] + CELL_GAP

        buffer = io.BytesIO()
        sheet.save(buffer, format="JPEG", quality=80, optimize=True, progressive=True)
        return buffer.getvalue()

    # ------------------------------------------------------------------ 출력

    def _report(self, items, groups):
        self.stdout.write(self.style.WARNING("[dry-run] DB에 쓰지 않습니다."))

        for group in groups:
            self.stdout.write(f"\n■ {group['title']} ({len(group['numbers'])}종)")

        self.stdout.write("")
        for it in items[:8]:
            self.stdout.write(
                f"  {it['no']:>3} {it['name']:<14} "
                f"연:{it['occurrence']:<16} 월:{it['overwinter']:<20} "
                f"여름기주:{it['host'] or '-'}"
            )

        blank = [it for it in items if not it["name"]]
        self.stdout.write(f"\n해충명 없음 {len(blank)}종 / 기출 표시 {sum(1 for i in items if i['is_past'])}종")
        for key in ("occurrence", "overwinter", "host"):
            filled = sum(1 for it in items if it[key])
            self.stdout.write(f"  {key}: {filled}/{len(items)}종")

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
            course, created = PestCourse.objects.get_or_create(
                name=name,
                defaults={"description": group["title"][:200], "order": order},
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

                question = PestQuestion(
                    course=course,
                    order=item["no"],
                    source_key=key,
                    name=item["name"],
                    occurrence=item.get("occurrence", ""),
                    overwinter=item.get("overwinter", ""),
                    host=item.get("host", ""),
                    taxon_order=item.get("taxon_order", ""),
                    taxon_family=item.get("taxon_family", ""),
                )
                digest = hashlib.sha256(blob).hexdigest()[:12]
                question.image.save(
                    f"pest_{item['no']:03d}_{digest}.jpg", ContentFile(blob), save=False
                )
                question.save()
                added += 1

            total_added += added
            self.stdout.write(f"  {course.name}: +{added}종 (총 {course.questions.count()})")

        self.stdout.write(self.style.SUCCESS(f"완료: 문제 {total_added}개 추가"))

    @staticmethod
    def _short_title(title):
        """'노린재목 진딧물과' 처럼 코스명에 쓸 짧은 제목."""
        title = title.replace("곤충강 ", "").replace("거미강 ", "")
        parts = [p.strip() for p in re.split(r"[,·]", title) if p.strip()]
        if len(parts) > 2:
            return f"{parts[0]} 외 {len(parts) - 1}과"
        return " ".join(title.split())[:60]
