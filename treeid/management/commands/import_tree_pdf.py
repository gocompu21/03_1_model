"""수목 식별 학습 PDF를 수목 암기 데이터로 임포트.

'2025 수목 식별 공부' 형식의 PDF를 읽어 TreeCourse / TreeQuestion 으로 적재한다.

PDF 구조 (전제):
    - 목차 페이지: "01. 소철" 형태로 10종씩 묶여 있다. 수목명은 여기서만 얻는다.
      (상세 페이지에는 수목명이 적혀 있지 않다)
    - 종별 상세 페이지: 사진 여러 장 + 특징 설명 + 종 번호.
      상세 페이지 1장이 1종이며 목차 순서와 일치한다.
    - 맨 뒤 가나다순 목록과 판권 페이지는 제외한다.

사진 위에 얹힌 설명 글자("잎은 2개씩 모여난다" 등)가 학습에 중요하므로
페이지를 통째로 렌더링해 이미지로 만든다. 수목명은 페이지에 적혀 있지
않아(목차에만 있음) 정답이 새지 않는다.

사용 예:
    python manage.py import_tree_pdf "2025 수목 식별 공부2.pdf" --dry-run
    python manage.py import_tree_pdf "2025 수목 식별 공부2.pdf"
    python manage.py import_tree_pdf "..." --replace
"""

import hashlib
import io
import re


from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from treeid.models import TreeCourse, TreeQuestion

# 목차 행: "01. 소철", "69. (속명) 피라칸타(Pyracantha )"
INDEX_ROW_RE = re.compile(r"^\s*(\d{1,3})\s*\.\s*(.+?)\s*$")
INDEX_TAIL = "수록 수목"  # 가나다순 목록 페이지 표시

# 종당 코스 묶음 크기 (목차가 10종씩 끊겨 있다)
COURSE_SIZE = 10

# 사진 한 칸의 렌더링 폭(px). 2열로 놓으므로 전체 폭은 약 950px이 된다.
# 모바일에서 한 칸이 화면 절반을 차지해 글자가 읽힌다.
CELL_WIDTH = 470
CELL_GAP = 8
MAX_PHOTOS = 8
# 장식용 작은 도형을 거르는 최소 배치 영역 (pt^2)
MIN_BOX_AREA = 500
# 종별 페이지로 인정할 최소 사진 칸 수 (표지는 배경 1~2장뿐)
MIN_PHOTOS_PER_PAGE = 3


class Command(BaseCommand):
    help = "수목 식별 학습 PDF를 수목 암기 코스로 임포트한다"

    def add_arguments(self, parser):
        parser.add_argument("pdf_file", help="PDF 파일 경로")
        parser.add_argument("--prefix", default="수목식별", help="코스명 접두어")
        parser.add_argument("--replace", action="store_true", help="기존 문제를 지우고 새로 넣는다")
        parser.add_argument("--dry-run", action="store_true", help="DB에 쓰지 않고 결과만 출력")
        parser.add_argument("--limit", type=int, default=0, help="앞에서 N종만 처리")

    def handle(self, *args, **opts):
        try:
            import pymupdf
        except ImportError:
            raise CommandError("pymupdf가 필요합니다: pip install pymupdf")

        try:
            doc = pymupdf.open(opts["pdf_file"])
        except Exception:
            raise CommandError(f"PDF를 열 수 없습니다: {opts['pdf_file']}")

        with doc:
            # (텍스트, 문단 블록 목록) 을 페이지 순서대로 모은다
            pages = [
                (page.get_text() or "", [b[4] for b in page.get_text("blocks")])
                for page in doc
            ]
            self.stdout.write(f"페이지 {len(pages)}개")

            names, index_pages = self._parse_index(pages)
            self.stdout.write(f"목차에서 수목명 {len(names)}종 수집")
            if not names:
                raise CommandError("목차를 찾지 못했습니다. PDF 구조를 확인하세요.")

            items = self._parse_details(doc, pages, names, index_pages)
            self.stdout.write(f"상세 페이지에서 {len(items)}종 파싱")

            missing = sorted(set(names) - {it["no"] for it in items})
            if missing:
                self.stderr.write(self.style.WARNING(f"상세를 못 찾은 번호: {missing[:20]}"))

            if opts["limit"]:
                items = items[: opts["limit"]]

            if opts["dry_run"]:
                self._report(items)
                return

            self._save(items, opts, doc)

    # ------------------------------------------------------------------ 파싱

    def _parse_index(self, pages):
        """목차에서 번호->수목명을 모으고, 목차 페이지 번호를 함께 반환."""
        names = {}
        index_pages = set()

        for i, (text, _blocks) in enumerate(pages, 1):
            rows = [INDEX_ROW_RE.match(ln) for ln in text.split("\n")]
            rows = [m for m in rows if m]
            # 번호 목록이 여러 줄 이어지는 페이지만 목차로 본다
            if len(rows) < 5:
                continue
            index_pages.add(i)
            for m in rows:
                no = int(m.group(1))
                name = self._clean_name(m.group(2))
                if name:
                    names[no] = name

        return names, index_pages

    @staticmethod
    def _clean_name(name):
        """'(속명) 피라칸타(Pyracantha )' 처럼 붙은 군더더기를 정리한다."""
        name = re.sub(r"\s+", " ", name).strip()
        name = re.sub(r"^\(속명\)\s*", "", name)
        name = re.sub(r"\s*\(\s*[A-Za-z][^)]*\)\s*$", "", name)  # 라틴 학명 괄호 제거
        return name.strip(" .")

    def _parse_details(self, doc, pages, names, index_pages):
        """목차를 뺀 나머지를 순서대로 종에 대응시킨다."""
        items = []
        expected = 1
        last = max(names) if names else 0

        for i, (text, blocks) in enumerate(pages, 1):
            if i in index_pages or INDEX_TAIL in text:
                continue
            if expected > last:
                break
            # 표지·판권은 배경 이미지 1~2장뿐이고, 종별 페이지는 사진 칸이
            # 격자로 여러 개다. 칸 크기가 페이지의 일부인 것만 센다.
            page_rect = doc[i - 1].rect
            photo_count = 0
            for info in doc[i - 1].get_image_info():
                x0, y0, x1, y1 = info["bbox"]
                w, h = x1 - x0, y1 - y0
                if w * h <= MIN_BOX_AREA:
                    continue
                if w > page_rect.width * 0.6 or h > page_rect.height * 0.9:
                    continue  # 페이지를 덮는 배경 이미지
                photo_count += 1
            if photo_count < MIN_PHOTOS_PER_PAGE:
                continue

            items.append({
                "no": expected,
                "name": names.get(expected, ""),
                "description": self._clean_description(blocks, expected),
                "page_no": i,  # 페이지 렌더링에 쓴다 (1-based)
            })
            expected += 1

        return items

    @staticmethod
    def _clean_description(blocks, no):
        """PDF 텍스트 블록을 설명 문단으로 정리한다.

        PDF는 좁은 칸에 맞춰 줄을 끊어 놓아, 줄 단위로 나누면 한 문장이
        여러 조각으로 쪼개진다. 블록(문단) 단위로 이어 붙여야 문장이 산다.
        """
        paragraphs = []
        for raw in blocks:
            # 줄바꿈은 공백 한 칸으로 잇는다. PDF가 좁은 칸에 맞춰 단어
            # 중간에서 끊은 경우가 많아 완벽히 복원할 수는 없지만,
            # 공백을 넣는 편이 붙여 쓰는 것보다 읽기 쉽다.
            text = re.sub(r"\s*\n\s*", " ", raw)
            text = re.sub(r"\s+", " ", text).strip()
            if not text:
                continue
            # 문단 앞뒤나 중간에 끼어든 종 번호 제거 (숫자로 홀로 선 것만)
            text = re.sub(rf"(?<![\d~.-])0?{no}(?![\d~.-])", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            # 페이지 번호 등 숫자·기호만 남은 문단은 버린다
            if not text or not re.search(r"[가-힣A-Za-z]", text):
                continue
            paragraphs.append(text)

        return "\n".join(paragraphs)[:2000]

    # ------------------------------------------------------------------ 이미지

    def _build_image(self, item, doc):
        """사진 칸 단위로 렌더링해 세로로 이어 붙인다.

        페이지를 통째로 렌더링하면 모바일에서 글자가 너무 작아지고,
        사진만 추출하면 사진 위에 얹힌 설명 글자가 빠진다. 그래서
        사진이 놓인 영역을 글자까지 포함해 잘라낸 뒤 크게 쌓는다.
        영역 렌더링이므로 PDF가 회전 배치한 사진도 자연히 바로 선다.
        """
        import pymupdf
        from PIL import Image

        page = doc[item["page_no"] - 1]

        # 사진이 놓인 영역을 페이지 안으로 잘라 정렬 (위 -> 아래, 왼 -> 오)
        boxes = []
        for info in page.get_image_info():
            box = pymupdf.Rect(info["bbox"]) & page.rect
            if box.width * box.height > MIN_BOX_AREA:
                boxes.append(box)
        boxes.sort(key=lambda b: (round(b.y0), round(b.x0)))
        boxes = self._dedupe_boxes(boxes)

        if not boxes:  # 배치 정보를 못 읽으면 페이지 전체로 대체
            boxes = [page.rect]

        crops = []
        for box in boxes[:MAX_PHOTOS]:
            zoom = CELL_WIDTH / box.width
            pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=box)
            crops.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))

        # 2열로 쌓는다. 1열로 세우면 세로가 7000px에 육박해 넘겨보기 어렵다.
        cols = 1 if len(crops) == 1 else 2
        rows = (len(crops) + cols - 1) // cols
        row_heights = [
            max(c.height for c in crops[r * cols:(r + 1) * cols]) for r in range(rows)
        ]

        width = CELL_WIDTH * cols + CELL_GAP * (cols + 1)
        height = CELL_GAP + sum(h + CELL_GAP for h in row_heights)
        sheet = Image.new("RGB", (width, height), (255, 255, 255))

        y = CELL_GAP
        for r in range(rows):
            for c, crop in enumerate(crops[r * cols:(r + 1) * cols]):
                x = CELL_GAP + c * (CELL_WIDTH + CELL_GAP) + (CELL_WIDTH - crop.width) // 2
                sheet.paste(crop, (x, y))
            y += row_heights[r] + CELL_GAP

        buffer = io.BytesIO()
        sheet.save(buffer, format="JPEG", quality=78, optimize=True, progressive=True)
        return buffer.getvalue()

    @staticmethod
    def _dedupe_boxes(boxes):
        """같은 자리에 겹쳐 놓인 영역은 하나만 남긴다."""
        kept = []
        for box in boxes:
            if any(abs(box.x0 - k.x0) < 3 and abs(box.y0 - k.y0) < 3 for k in kept):
                continue
            kept.append(box)
        return kept

    # ------------------------------------------------------------------ 출력

    def _report(self, items):
        self.stdout.write(self.style.WARNING("[dry-run] DB에 쓰지 않습니다."))
        for it in items[:10]:
            head = it["description"].split("\n")[0][:52]
            self.stdout.write(f"  {it['no']:>3} {it['name']:<16} {head}")
        self.stdout.write(f"\n총 {len(items)}종")
        self.stdout.write(f"  이름 있음: {sum(1 for it in items if it['name'])}종")
        self.stdout.write(f"  설명 있음: {sum(1 for it in items if it['description'])}종")

    # ------------------------------------------------------------------ 저장

    @transaction.atomic
    def _save(self, items, opts, doc):
        prefix = opts["prefix"]
        total_added = 0

        for start in range(0, len(items), COURSE_SIZE):
            chunk = items[start:start + COURSE_SIZE]
            order = start // COURSE_SIZE + 1
            first, last = chunk[0], chunk[-1]
            name = f"{prefix} {order:02d}. {first['name']} ~ {last['name']}"

            course, created = TreeCourse.objects.get_or_create(
                name=name,
                defaults={
                    "description": f"{first['no']}~{last['no']}번",
                    "order": order,
                },
            )
            if not created:
                course.order = order
                course.save(update_fields=["order"])

            if opts["replace"]:
                course.questions.all().delete()

            existing = set(course.questions.values_list("source_key", flat=True))
            added = 0

            for item in chunk:
                key = f"pdf-{item['no']:03d}"
                if key in existing:
                    continue

                blob = self._build_image(item, doc)
                if not blob:
                    self.stderr.write(f"  [{item['no']}] 사진이 없어 건너뜀")
                    continue

                q = TreeQuestion(
                    course=course,
                    order=item["no"],
                    source_key=key,
                    name=item["name"],
                    description=item["description"],
                )
                digest = hashlib.sha256(blob).hexdigest()[:12]
                q.image.save(f"tree_{item['no']:03d}_{digest}.jpg", ContentFile(blob), save=False)
                q.save()
                added += 1

            total_added += added
            self.stdout.write(f"  {course.name}: +{added}종 (총 {course.questions.count()})")

        self.stdout.write(self.style.SUCCESS(f"완료: 문제 {total_added}개 추가"))
