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

# 페이지 렌더링 폭(px). 원본 페이지가 약 369pt라 3배 정도로 잡는다.
RENDER_WIDTH = 1100
# 표지·판권 등을 걸러낼 때 쓰는 최소 사진 크기
MIN_PHOTO_AREA = 20000


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
            from pypdf import PdfReader
        except ImportError:
            raise CommandError("pypdf가 필요합니다: pip install pypdf")

        try:
            reader = PdfReader(opts["pdf_file"])
        except FileNotFoundError:
            raise CommandError(f"파일을 찾을 수 없습니다: {opts['pdf_file']}")

        pages = [(p, p.extract_text() or "") for p in reader.pages]
        self.stdout.write(f"페이지 {len(pages)}개")

        names, index_pages = self._parse_index(pages)
        self.stdout.write(f"목차에서 수목명 {len(names)}종 수집")
        if not names:
            raise CommandError("목차를 찾지 못했습니다. PDF 구조를 확인하세요.")

        items = self._parse_details(pages, names, index_pages)
        self.stdout.write(f"상세 페이지에서 {len(items)}종 파싱")

        missing = sorted(set(names) - {it["no"] for it in items})
        if missing:
            self.stderr.write(self.style.WARNING(f"상세를 못 찾은 번호: {missing[:20]}"))

        if opts["limit"]:
            items = items[: opts["limit"]]

        if opts["dry_run"]:
            self._report(items)
            return

        try:
            import pymupdf
        except ImportError:
            raise CommandError("pymupdf가 필요합니다: pip install pymupdf")

        with pymupdf.open(opts["pdf_file"]) as doc:
            self._save(items, opts, doc)

    # ------------------------------------------------------------------ 파싱

    def _parse_index(self, pages):
        """목차에서 번호->수목명을 모으고, 목차 페이지 번호를 함께 반환."""
        names = {}
        index_pages = set()

        for i, (_, text) in enumerate(pages, 1):
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

    def _parse_details(self, pages, names, index_pages):
        """목차를 뺀 나머지를 순서대로 종에 대응시킨다."""
        items = []
        expected = 1
        last = max(names) if names else 0

        for i, (page, text) in enumerate(pages, 1):
            if i in index_pages or INDEX_TAIL in text:
                continue
            if expected > last:
                break
            # 표지·판권 등 사진이 거의 없는 앞 페이지는 건너뛴다
            try:
                photo_count = sum(
                    1 for im in page.images
                    if self._is_photo(im)
                )
            except Exception:
                photo_count = 0
            if photo_count < 2:
                continue

            items.append({
                "no": expected,
                "name": names.get(expected, ""),
                "description": self._clean_description(text, expected),
                "page": page,
                "page_no": i,  # 페이지 렌더링에 쓴다 (1-based)
            })
            expected += 1

        return items

    @staticmethod
    def _is_photo(embedded):
        from PIL import Image
        try:
            img = Image.open(io.BytesIO(embedded.data))
            return img.width * img.height >= MIN_PHOTO_AREA
        except Exception:
            return False

    @staticmethod
    def _clean_description(text, no):
        """설명문에서 종 번호를 떼고 줄바꿈을 정리한다."""
        lines = []
        for raw in text.split("\n"):
            line = raw.strip()
            if not line:
                continue
            # 줄에 붙은 종 번호 제거 ("61", "03 암수한그루" 등)
            line = re.sub(rf"(?<!\d){no:02d}(?!\d)", " ", line)
            line = re.sub(rf"(?<!\d){no}(?!\d)", " ", line, count=1) if no >= 10 else line
            line = re.sub(r"\s+", " ", line).strip()
            if line:
                lines.append(line)
        return "\n".join(lines)[:2000]

    # ------------------------------------------------------------------ 이미지

    def _build_image(self, item, doc):
        """페이지를 통째로 렌더링한다.

        사진 위에 얹힌 설명 글자가 학습 자료의 핵심이라 사진만 뽑지 않는다.
        페이지 렌더링이므로 PDF가 회전 배치한 사진도 자연히 바로 선다.
        """
        import pymupdf
        from PIL import Image

        page = doc[item["page_no"] - 1]
        zoom = RENDER_WIDTH / page.rect.width
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))

        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=82, optimize=True, progressive=True)
        return buffer.getvalue()

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
