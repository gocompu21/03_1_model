"""
쪽집게 노트 마크다운 파일을 DB에 import.
EC2에서 실행: python save_study_note.py

data/ 디렉토리에서 수목병리학_note_ch*.md 파일을 읽어서
StudyNote 모델에 update_or_create로 저장.
"""
import os, sys, glob, re, django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from exam.models import Subject, StudyNote

# 과목명 → Subject 매핑
SUBJECT_NAME = "수목병리학"

subject = Subject.objects.get(name__contains=SUBJECT_NAME.replace("학", ""))
print(f"과목: {subject.name} (pk={subject.pk})")

# data/ 디렉토리에서 note_ch*.md 파일 찾기
base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, "data")

# 패턴: pathology_note_ch1.md, pathology_note_ch2.md, ...
pattern = os.path.join(data_dir, "pathology_note_ch*.md")
files = sorted(glob.glob(pattern), key=lambda f: int(re.search(r"ch(\d+)", f).group(1)))

if not files:
    # 단일 파일 모드: 수목병리학_쪽집게노트.md
    single_file = os.path.join(data_dir, "수목병리학_쪽집게노트.md")
    if os.path.exists(single_file):
        print(f"단일 파일 모드: {single_file}")
        with open(single_file, "r", encoding="utf-8") as f:
            content = f.read()
        # ## 제N장 기준으로 분할
        chapters = re.split(r"(?=^## 제\d+장)", content, flags=re.MULTILINE)
        chapters = [ch.strip() for ch in chapters if ch.strip() and ch.strip().startswith("## 제")]
        for idx, ch_content in enumerate(chapters):
            m = re.match(r"## (제\d+장\.\s*.+)", ch_content.split("\n")[0])
            title = m.group(1).strip() if m else f"제{idx+1}장"
            note, created = StudyNote.objects.update_or_create(
                subject=subject,
                order=idx + 1,
                defaults={"title": title, "content": ch_content},
            )
            action = "생성" if created else "갱신"
            print(f"  [{action}] order={idx+1}: {title}")
        print(f"\n완료: {len(chapters)}개 노트 저장")
    else:
        print(f"파일을 찾을 수 없습니다: {pattern} 또는 {single_file}")
        sys.exit(1)
else:
    print(f"발견된 파일: {len(files)}개")
    for idx, filepath in enumerate(files):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        # 제목 추출
        m = re.match(r"## (제\d+장\.\s*.+)", content.split("\n")[0])
        title = m.group(1).strip() if m else f"제{idx+1}장"
        note, created = StudyNote.objects.update_or_create(
            subject=subject,
            order=idx + 1,
            defaults={"title": title, "content": content},
        )
        action = "생성" if created else "갱신"
        print(f"  [{action}] order={idx+1}: {title} ({os.path.basename(filepath)})")
    print(f"\n완료: {len(files)}개 노트 저장")
