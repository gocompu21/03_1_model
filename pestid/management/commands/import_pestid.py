"""해충 식별 마라톤 JSON 덤프를 DB로 임포트.

브라우저 콘솔에서 marathonList를 JSON으로 저장한 파일을 읽어
PestCourse / PestQuestion 으로 적재한다.

기대하는 형식 (원본 marathonList 구조):
    [
      {
        "dataUrl": "data:image/jpeg;base64,....",
        "answers": {"name": "...", "occurrence": "...",
                    "overwinter": "...", "host": "..."}
      },
      ...
    ]

사용 예:
    python manage.py import_pestid marathon1.json --course "해충식별 1"
    python manage.py import_pestid marathon2.json --course "해충식별 2" --replace
"""

import base64
import binascii
import hashlib
import json
import re

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from pestid.models import PestCourse, PestQuestion

DATAURL_RE = re.compile(r"^data:image/(?P<ext>[a-zA-Z0-9.+-]+);base64,(?P<data>.+)$", re.S)

EXT_MAP = {"jpeg": "jpg", "jpg": "jpg", "png": "png", "gif": "gif", "webp": "webp"}


class Command(BaseCommand):
    help = "해충 식별 마라톤 JSON 덤프를 임포트한다"

    def add_arguments(self, parser):
        parser.add_argument("json_file", help="marathonList를 저장한 JSON 파일 경로")
        parser.add_argument("--course", required=True, help="코스명 (없으면 생성)")
        parser.add_argument("--description", default="", help="코스 설명")
        parser.add_argument(
            "--replace",
            action="store_true",
            help="해당 코스의 기존 문제를 모두 지우고 새로 넣는다",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="DB에 쓰지 않고 파싱 결과만 확인한다",
        )

    def handle(self, *args, **opts):
        path = opts["json_file"]
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f"파일을 찾을 수 없습니다: {path}")
        except json.JSONDecodeError as e:
            raise CommandError(f"JSON 파싱 실패: {e}")

        if not isinstance(data, list):
            raise CommandError("최상위가 배열이 아닙니다. marathonList를 그대로 저장했는지 확인하세요.")

        self.stdout.write(f"항목 {len(data)}개 발견")

        parsed, skipped = self._parse(data)
        self.stdout.write(f"파싱 성공 {len(parsed)}개 / 건너뜀 {skipped}개")

        if not parsed:
            raise CommandError("적재할 항목이 없습니다.")

        if opts["dry_run"]:
            self.stdout.write(self.style.WARNING("[dry-run] DB에 쓰지 않고 종료합니다."))
            for i, item in enumerate(parsed[:5], 1):
                self.stdout.write(
                    f"  {i}. {item['answers'].get('name', '(이름없음)')} "
                    f"| 이미지 {len(item['blob'])} bytes | 항목 {len(item['answers'])}개"
                )
            return

        self._save(parsed, opts)

    def _parse(self, data):
        """dataUrl과 answers를 검증하며 파싱한다."""
        parsed, skipped = [], 0

        for idx, row in enumerate(data):
            if not isinstance(row, dict):
                skipped += 1
                continue

            data_url = row.get("dataUrl") or row.get("imageData") or ""
            m = DATAURL_RE.match(data_url.strip()) if data_url else None
            if not m:
                self.stderr.write(f"  [{idx}] dataUrl 형식이 아니어서 건너뜀")
                skipped += 1
                continue

            try:
                blob = base64.b64decode(m.group("data"))
            except (binascii.Error, ValueError) as e:
                self.stderr.write(f"  [{idx}] base64 디코드 실패: {e}")
                skipped += 1
                continue

            answers = row.get("answers") or {}
            answers = {
                k: str(v).strip()
                for k, v in answers.items()
                if k in PestQuestion.FIELD_LABELS and str(v).strip()
            }
            if not answers:
                self.stderr.write(f"  [{idx}] 정답 항목이 비어 있어 건너뜀")
                skipped += 1
                continue

            ext = EXT_MAP.get(m.group("ext").lower(), "png")
            # 이미지 내용 해시를 원본 식별자로 삼아 재실행 시 중복을 막는다
            digest = hashlib.sha256(blob).hexdigest()[:32]

            parsed.append({"blob": blob, "ext": ext, "answers": answers, "key": digest})

        return parsed, skipped

    @transaction.atomic
    def _save(self, parsed, opts):
        course, created = PestCourse.objects.get_or_create(
            name=opts["course"],
            defaults={"description": opts["description"]},
        )
        self.stdout.write(
            f"코스 {'생성' if created else '사용'}: {course.name} (id={course.id})"
        )

        if opts["replace"]:
            removed = course.questions.count()
            course.questions.all().delete()
            self.stdout.write(self.style.WARNING(f"기존 문제 {removed}개 삭제"))

        existing = set(course.questions.values_list("source_key", flat=True))
        added = duplicated = 0

        for i, item in enumerate(parsed, 1):
            if item["key"] in existing:
                duplicated += 1
                continue

            q = PestQuestion(
                course=course,
                order=i,
                source_key=item["key"],
                **item["answers"],
            )
            q.image.save(
                f"{course.id}_{item['key'][:12]}.{item['ext']}",
                ContentFile(item["blob"]),
                save=False,
            )
            q.save()
            existing.add(item["key"])
            added += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"완료: 추가 {added}개, 중복 건너뜀 {duplicated}개, "
                f"코스 총 {course.questions.count()}개"
            )
        )
