# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

나무의사 자격시험 대비 학습 플랫폼 (Forest Doctor Certification Exam Study Platform). Django 6.0 기반 웹 애플리케이션으로, 기출문제 풀이, AI 해설 생성, 용어 사전, 모의고사 기능을 제공한다.

## Commands

```bash
# 개발 서버 실행
python manage.py runserver

# 마이그레이션
python manage.py makemigrations
python manage.py migrate

# Django shell
python manage.py shell

# 정적 파일 수집 (배포 시)
python manage.py collectstatic
```

## Architecture

### Django Apps
- **exam**: 기출문제 관리 (Question, Exam, Subject, UserExamAttempt 모델). 회차별 문제, 5지선다 보기, 해설, 인포그래픽, 나레이션 포함
- **glossary**: 용어 사전 (Term, TermReference 모델). 과목별 용어 정의 및 문제/챕터 연결
- **study**: 학습 기록 및 Q&A (StudyQnA, StudyViewLog 모델)
- **chat**: AI 채팅 기록 (ChatHistory 모델). Gemini API 기반
- **practice**: 연습문제
- **pestid**: 해충 식별 퀴즈·암기 (PestCourse, PestQuestion, PestAttempt, PestBookmark). 176종
- **diseaseid**: 병해 암기 (DiseaseCourse, DiseaseQuestion, DiseaseBookmark). 154종
- **treeid**: 수목 암기 (TreeCourse, TreeQuestion, TreeBookmark). 120종
- **mock_exam**: 모의고사
- **notebook**: 학습 노트
- **bbs**: 게시판
- **accounts**: 사용자 인증 및 세션 추적 미들웨어
- **mypage**: 사용자 마이페이지
- **dashboard**: 관리자 대시보드

### External APIs
- **Google Gemini**: 해설 생성, 인포그래픽 생성, TTS 나레이션 (GEMINI_API_KEY via .env)
- **REST Framework + SimpleJWT**: 모바일 앱용 API 인증

### Database (PostgreSQL)

- **Engine**: PostgreSQL 16
- **DB**: `namu_doctor`
- **User/Password**: EC2의 `.env` 참조
- 환경변수 기반 전환: `.env`에 `DB_ENGINE` 등 설정 시 PostgreSQL, 미설정 시 SQLite 폴백 (로컬 개발용)
- SQLite 백업 파일: `db.sqlite3` (레거시, 52MB)

#### .env DB 설정 (EC2)

```
DB_ENGINE=django.db.backends.postgresql
DB_NAME=namu_doctor
DB_USER=<.env 참조>
DB_PASSWORD=<.env 참조>
DB_HOST=localhost
DB_PORT=5432
```

## Key Files

- `config/settings.py`: Django 설정, GEMINI_API_KEY, REST Framework/JWT 설정
- `exam/models.py`: Question, Exam, Subject, TopicQuestionSet 등 핵심 모델
- `glossary/models.py`: Term, TermReference - 용어 사전 시스템
- `fileSearchStore.py`: Google GenAI File Search 유틸리티

## Batch Scripts (프로젝트 루트)

루트에 있는 Python 스크립트들은 일회성 데이터 처리/마이그레이션용:
- `batch_fill_*`: AI로 용어 설명 일괄 생성
- `import_*`: 엑셀/JSON에서 데이터 임포트
- `generate_*`: 인포그래픽, 나레이션, HTML 해설 생성
- `check_*`, `debug_*`: 데이터 검증 및 디버깅

## Production Server

- **도메인**: `studynamu.com`
- **Host**: `ubuntu@studynamu.com`
- **SSH 키**: `C:\AWS\myServer-key-pair.pem`
- **Path**: `/home/ubuntu/myproject/03_1_model/`
- **가상환경**: `source ~/myproject/venv/bin/activate` (.bashrc에 자동 활성화)
- **서비스**: Gunicorn + Nginx

```bash
# SSH 접속
ssh -o ServerAliveInterval=60 -i "C:\AWS\myServer-key-pair.pem" ubuntu@studynamu.com

# 프로젝트 디렉토리
cd /home/ubuntu/myproject/03_1_model/

# 배포 (pull + 재시작)
git pull && sudo systemctl restart gunicorn
```

### SQLite → PostgreSQL 마이그레이션 이력

2026-02-25 완료. 주요 이슈 및 해결:

- **migration 0006** (`exam/migrations/0006_alter_question_answer.py`): IntegerField→JSONField 변환 시 PostgreSQL에서 `cannot cast integer to jsonb` 에러. `SeparateDatabaseAndState` + `RunPython`으로 `to_jsonb()` 캐스팅 처리
- **study/signals.py**: `post_save` 시그널에 `raw=False` 체크 추가. `loaddata` 시 시그널이 중복 레코드를 생성하는 문제 방지
- **dumpdata 옵션**: `--natural-foreign` 사용, `--natural-primary` 미사용 (auth.User PK 충돌 방지). `--exclude=contenttypes --exclude=auth.permission --exclude=admin.logentry`

## Git Conventions

- 커밋 메시지는 **한글**로 작성
- 예시: `성능 개선: 용어 매칭 AJAX 지연 로딩 구현`
- **커밋 시 항상 push까지 함께 실행**

## UI Components

### Image Modal (Lightbox)
이미지 모달 구현 시 다음 기능을 기본으로 포함:

**필수 기능:**
- **더블탭/더블클릭 줌**: 2.5배 확대/축소 토글 (0.25s ease-out 애니메이션)
- **핀치 줌**: 두 손가락으로 1x ~ 5x 부드러운 확대
- **한 손가락 패닝**: 확대 상태에서 드래그로 이미지 이동
- **마우스 휠 줌**: 데스크탑에서 휠로 확대/축소
- **마우스 드래그 패닝**: 데스크탑에서 드래그로 이동
- **ESC 키 / 배경 클릭**: 모달 닫기

**핵심 구현 사항:**
```css
.lightbox-img {
    touch-action: none;           /* 모바일 스크롤 방지 필수 */
    will-change: transform;
    transform-origin: center center;
}
.lightbox-img.animating {
    transition: transform 0.25s ease-out;  /* 더블탭 시 부드러운 애니메이션 */
}
```

```javascript
// Transform 순서: scale 먼저, translate 나중 (부드러운 패닝)
lightboxImg.style.transform = `scale(${scale}) translate(${posX}px, ${posY}px)`;

// 터치 상태 분리 (핀치 → 패닝 자연스러운 전환)
let isPinching = false;  // 두 손가락 핀치 중
let isPanning = false;   // 한 손가락 패닝 중

// 핀치 줌 계산
const scaleRatio = currentDistance / startDistance;
scale = Math.min(Math.max(startScale * scaleRatio, 1), 5);

// 패닝 범위 제한
const maxPan = (scale - 1) * 150;
posX = Math.min(Math.max(posX, -maxPan), maxPan);

// 이벤트 리스너 옵션
element.addEventListener('touchstart', handler, { passive: false });
```

**참고 구현:** `practice/templates/practice/chapter_detail.html`의 라이트박스 섹션

## 쪽집게 노트 (StudyNote) 생성 파이프라인

### StudyNote 모델 (study/models.py)

| 필드 | 설명 |
|------|------|
| `subject` | FK → Subject (수목병리학/수목해충학/수목생리학/산림토양학/수목관리학) |
| `title` | 장 제목 (예: "제1장. 수목병의 개념") |
| `content` | 마크다운 내용 (교재형 서술문) |
| `order` | 장 순서 (1~15) |

- unique_together: `(subject, order)`
- 총 45개 노트 (5과목, 각 8~10장)
- 5~12회 기출문제 기반 (1~4회 제외)

### 생성 스크립트

**`generate_study_notes.py`** — 과목 단위 노트 생성 워커

6단계 파이프라인:
- **Step 0**: DB에서 과목 문제 JSON 추출 (`{prefix}_questions.json`)
- **Step 1**: Gemini Filestore(교과서 PDF RAG)로 목차 생성 (`{prefix}_toc.json`)
- **Step 2**: 문제를 목차 절에 분류 (`{prefix}_classification.json`)
- **Step 3**: 장별 마크다운 콘텐츠 생성 (`data/{prefix}_note_ch{N}.md`)
- **Step 4**: 커버리지 검증 (누락 문제 확인)
- **Step 5**: DB import (`StudyNote.objects.update_or_create`)

```bash
# 전체 실행
python generate_study_notes.py 수목병리학

# 단계별 실행 (병렬 오케스트레이션용)
python generate_study_notes.py 수목병리학 --phase phase1    # Step 0-2
python generate_study_notes.py 수목병리학 --phase chapter --chapter 3  # Step 3 (3장만)
python generate_study_notes.py 수목병리학 --phase phase3    # Step 4-5

# 캐시 무시 재생성
python generate_study_notes.py 수목병리학 --force
```

**`generate_notes_parallel.py`** — 3-Phase 병렬 생성 런처

- Phase 1: 5과목 동시 Step 0-2 (문제추출 + 목차 + 분류)
- Phase 2: 전 과목 전 장 동시 Step 3 (장별 콘텐츠 생성, MAX_WORKERS=10)
- Phase 3: 5과목 동시 Step 4-5 (검증 + DB import)

```bash
python generate_notes_parallel.py                          # 전체
python generate_notes_parallel.py --phase 2 --workers 5    # Phase 2만, 워커 5개
python generate_notes_parallel.py --subjects 수목병리학 수목해충학  # 특정 과목만
python generate_notes_parallel.py --force                  # 캐시 무시
```

### Gemini Filestore (교과서 PDF RAG)

- `fileSearchStore.py`: `GeminiStoreManager` — Google GenAI File Search 유틸리티
- 5과목 각각 교과서 PDF가 Gemini Cloud에 업로드되어 있음
- 과목별 Store ID가 `fileSearchStore.py`에 하드코딩
- Step 1(목차)과 Step 3(장별 콘텐츠)에서 교과서 RAG 활용
- 클라우드 API이므로 로컬/서버 어디서든 동일하게 사용 가능

### SUBJECT_PREFIX 매핑

```python
SUBJECT_PREFIX = {
    "수목병리학": "pathology",
    "수목해충학": "entomology",
    "수목생리학": "physiology",
    "산림토양학": "soil",
    "수목관리학": "management",
}
```

### 캐시 파일 정리

재생성 전 캐시 삭제 필요:
```bash
rm -f *_questions.json *_classification.json *_toc.json data/*_note_ch*.md
```

## 인포그래픽 이미지 생성

### Question.infographic_image

- `ImageField(upload_to="questions/explanations/")`
- Gemini 이미지 생성 API로 문제 해설 인포그래픽 자동 생성

### 생성 스크립트

**`app_generate_infographic.py`** — 단일 문제 인포그래픽 생성
**`app_generate_infographic_batch.py`** — 배치 생성 (기존)
**`generate_exam12_infographic_worker.py`** — 12회 전용 워커 (범위 지정)
**`generate_exam12_infographics.py`** — 12회 병렬 런처 (MAX_WORKERS=3)

```bash
# 서버에서 실행 (914MB RAM 제한으로 최대 3 워커)
nohup python generate_exam12_infographics.py --model gemini-3.1-flash-image-preview > /tmp/infographic.log 2>&1 &

# 진행 확인
python -c "import os,django;os.environ['DJANGO_SETTINGS_MODULE']='config.settings';django.setup();from exam.models import Question;print(Question.objects.filter(exam__round_number=12).exclude(infographic_image='').count())"
```

### 사용 가능한 이미지 모델

- `gemini-3.1-flash-image-preview`: 빠르고 저렴 (~$0.067/장, 12회 125문제 $8.4)
- `gemini-3-pro-image-preview`: 고품질이지만 느리고 비쌈 (~$0.134/장, 매우 느림)
- 914MB 서버에서는 Flash 권장 (Pro는 메모리/시간 부담)

## 12회 기출 데이터

- 2026년 2월 시행 나무의사 12회 필기시험
- 총 125문제 (5과목 × 25문제), PDF에서 Gemini로 파싱
- `exam12_full_data.json`: 전체 데이터 (문제/보기/정답/해설)
- `load_exam12.py`: 서버 import 스크립트 (`update_or_create` 기반)
- 인포그래픽 125/125 생성 완료 (`gemini-3.1-flash-image-preview`)
- `study/templates/study/index.html`: 12회 카드 날짜 `2026.2`

### 서버 배포 절차

```bash
# 1. 로컬에서 JSON 추출 후 git push
# 2. SSH 접속
ssh -o ServerAliveInterval=60 -i "C:\AWS\myServer-key-pair.pem" ubuntu@studynamu.com
# 3. 서버에서
cd ~/myproject/03_1_model && git pull
python load_exam12.py              # DB import
sudo systemctl restart gunicorn    # 서비스 재시작
```

## DVD 암기 (`/dvd/`)

사진을 보고 정답을 확인하며 넘겨보는 학습 화면. 세 앱이 같은 구조를 공유한다.
카드 순서: 수목 암기 → 병해 암기 → 해충 암기 → 해충 식별(퀴즈).

| 앱 | 화면 | 종수 | 정답 항목 | 출처 PDF |
|---|---|---|---|---|
| `treeid` | `/treeid/memorize/` | 120 | 수목명 + 특징 설명 | 2025 수목 식별 공부2 |
| `diseaseid` | `/diseaseid/memorize/` | 154 | 병명·기주·병원균·추가사항 | 2026 병해 식별공부 |
| `pestid` | `/pestid/memorize/` | 176 | 해충명·연발생횟수·월동태·여름기주 | 2026 해충식별공부 |

### 공통 동작

- 사진 → **다음**(정답 보기) → 정답 오버레이 → **다음**(다음 종) 반복
- 정답은 **사진 위에 겹쳐** 표시한다 (아래 카드가 아니라 오버레이)
- 하단 바: `[◀] n/전체 [다음] [목록]` + 관심 등록 체크박스
- 헤더에서 모드 전환 (전체 / 기출 / 관심). 현재 모드를 뺀 나머지를 항상 노출한다
- 관심 등록은 **사용자별**(`*Bookmark` 모델, `unique_together`)
- 사진 위 **'한 화면' 토글**: `max-height`로 스크롤 없이 전체 보기, 선택은 localStorage에 저장
  (키가 앱마다 다르다: `treeidFit` / `diseaseidFit` / `pestidFit`)
- 기출 정보는 병해·해충에만 있다. 수목 PDF에는 없어 기출 모드·필터를 넣지 않았다

### 화면에서 자주 어긋났던 것들

- **목록 필터는 `display` 직접 조작 금지.** `display=''`로 되돌리면 CSS의 `display:grid`가
  복원되지 않아 표가 깨진다. `.filtered { display:none }` 클래스로 토글할 것
- **정답 오버레이 스크롤**: `scrollIntoView({block:'end'})`는 하단 고정 바에 가린다.
  바 높이를 실측해 그만큼 더 내린다 (`scrollInfoIntoView`)
- **`annotate()`는 `Meta.ordering`을 무너뜨린다.** 코스 목록이 무작위로 나왔던 원인.
  `.order_by()`를 명시할 것
- 코스명에 정답이 들어 있으면 화면뿐 아니라 **payload에서도 빼야 한다**
  (수목 코스명 "01. 소철 ~ 노간주나무" → 소스 보기로 정답 노출)

### PDF → 이미지 변환 방침 (앱마다 다르다)

| | 해충 · 병해 | 수목 |
|---|---|---|
| 방식 | 사진 이미지만 추출해 합성 | **영역 렌더링** (PyMuPDF) |
| 이유 | 페이지 본문에 정답이 글자로 적혀 있음 | 페이지에 수목명이 없어 글자를 넣어도 안전 |
| 글자 | 사진에 인코딩된 것만 남음 | 설명 글자 포함 |

- 수목은 `page.get_image_info()`로 **사진 칸 좌표를 읽어 글자까지 함께 잘라낸다.**
  칸별로 자르므로 PDF가 회전 배치한 사진(`cm` 변환행렬)도 자연히 바로 선다
- 페이지를 통째로 렌더링하면 모바일에서 글자가 너무 작다. **칸별로 잘라 2열**로 쌓는다
  (1열은 세로 6800px·83MB, 2열은 2340px·48MB)
- 설명문은 **텍스트 블록(문단) 단위**로 읽는다. 줄 단위로 나누면 PDF가 칸 폭에 맞춰
  끊은 줄이 그대로 항목이 되어 한 문장이 여러 글머리표로 쪼개진다 (해당화 13개 → 5개)

### 재임포트 후 배포 (세 앱 공통, 사고 잦음)

`--replace`는 행을 지우고 새로 넣으므로 **PK가 새로 발급된다.** 픽스처를 그냥 올리면
덮어써지지 않고 **옛 레코드가 남아 문제가 2배가 된다.** 서버에서 먼저 지울 것.

```bash
# 로컬
python manage.py import_tree_pdf "..." --replace     # 또는 import_disease_pdf / import_pest_pdf
python manage.py dumpdata treeid.TreeCourse treeid.TreeQuestion --indent=2 -o tree_fixture.json
tar -czf tree_media.tar.gz -C media treeid           # Git Bash에서 /c/... POSIX 경로
scp -i "C:\AWS\myServer-key-pair.pem" tree_media.tar.gz tree_fixture.json ubuntu@studynamu.com:/tmp/

# 서버
cd ~/myproject/03_1_model
~/myproject/venv/bin/python -c "
import os,django; os.environ['DJANGO_SETTINGS_MODULE']='config.settings'; django.setup()
from treeid.models import TreeQuestion; TreeQuestion.objects.all().delete()"
rm -rf media/treeid && tar -xzf /tmp/tree_media.tar.gz -C media
~/myproject/venv/bin/python manage.py loaddata /tmp/tree_fixture.json
```

- 코스는 PK가 유지되므로(get_or_create) 지우지 않는다. 코스를 지우면 사용자 기록이
  cascade로 함께 사라진다
- 검증: 문제 수, `order` 연속성, 이미지 파일 누락 0, 중복 이미지 0
- 로컬 재임포트 시 이전 이미지가 고아로 남는다. DB가 참조하지 않는 `media/<앱>/` 파일 삭제
- 미디어는 모두 `.gitignore` (`media/pestid/`, `media/diseaseid/`, `media/treeid/`)

## 해충 식별 퀴즈 (pestid 앱)

해충 사진을 보고 **해충명 / 연 발생횟수 / 월동태 / 여름기주**를 맞추는 퀴즈.
객관식·주관식 두 모드가 있고, 채점은 서버(`pestid/views.py:grade`)에서만 한다.

- `PestCourse`: 코스(분류군 단위) / `PestQuestion`: 사진 1장 + 정답 4항목 / `PestAttempt`: 도전 기록
- 정답 필드는 **쉼표가 별해 구분자**다. 첫 값이 객관식 보기와 정답 표시에 쓰이고,
  나머지는 주관식에서 정답으로 인정된다. 채점 시 공백은 무시한다.
  예: `3령약충 또는 성충, 3령약충, 성충`
- 따라서 한 덩어리인 값에 쉼표를 넣으면 정답이 잘려 보인다 (`3령약충,성충` → 표시 `3령약충`)

### PDF → 퀴즈 임포트

`pestid/management/commands/import_pest_pdf.py` — '2026 해충 식별 공부' 형식 PDF 전용.
2026-07-30 기준 v1.0(176종, 204쪽)을 18개 코스로 적재 완료.

```bash
python manage.py import_pest_pdf "2026 해충식별공부 v1.0(게시용).pdf" --dry-run  # 파싱 검증
python manage.py import_pest_pdf "2026 해충식별공부 v1.0(게시용).pdf"            # 적재
python manage.py import_pest_pdf "..." --replace                              # 기존 문제 교체
```

파싱 전제 (PDF 구조가 바뀌면 여기부터 확인):

- 종별 상세 페이지에 사진과 `기주:` `여름기주:` `연 발생횟수:` `월동태:` 라벨이 있고,
  페이지 어딘가에 **종 번호가 홀로** 적혀 있다 (`01`, `17`, `176`). 번호 없는 페이지는
  직전 종의 추가 사진 페이지로 묶인다
- **해충명은 상세 페이지에 없다.** 분류군별 요약표(`해충명 연 발생횟수 월동태 비고`)에서만 얻는다
- 요약표 표기를 대표 정답으로, 상세 페이지 표기를 별해로 합친다 (요약 `유충` + 상세 `노숙유충`)
- 상세 페이지 텍스트에는 정답이 그대로 적혀 있으므로 **페이지를 통째로 렌더링하면 안 된다.**
  사진만 추출해 한 장으로 합성한다 (`_build_image`)

### 서버 배포

절차는 **[재임포트 후 배포](#재임포트-후-배포-세-앱-공통-사고-잦음)** 참조 (세 앱 공통).
서버 가용 메모리가 약 275MB뿐이라 40MB PDF를 서버에서 파싱하지 않고,
**로컬에서 임포트 → 픽스처와 이미지를 전송**한다.

- 2026-07-30 사고: `--replace` 후 서버 문제를 지우지 않고 loaddata 해서 **352개로 중복**됐다.
  옛 레코드는 이미지가 교체된 뒤라 사진이 깨진 상태로 남았다
- 뷰·템플릿을 고쳤으면 `sudo systemctl restart gunicorn` 필요 (데이터만 바뀌면 불필요)

### 사진 크기

- 원본 PDF 사진은 폭 중앙값 약 720px. **2열로 합성하면 사진이 절반으로 줄어 작아 보인다**
- 그래서 3장 이하는 세로 1열로 쌓는다 (`SINGLE_COLUMN_MAX`). 시트 폭 `SHEET_WIDTH = 1000`
- 암기 화면 컨테이너는 960px. 사진 한 장이 데스크탑 약 945px, 모바일 약 344px로 보인다
- 세로가 길어진 대신 사진 위 **'한 화면' 토글**로 `max-height`를 걸어 스크롤 없이 볼 수 있다
- 전체 이미지 용량 약 33MB (JPEG quality 80, optimize, progressive)
- 검증: 176문제의 이미지 파일 존재 확인 → `/pestid/` 200 → `/media/pestid/<파일>` 200

## 회원 가입 승인 (accounts 앱)

2026-08-02 봇 가입이 확인되어(무작위 아이디 `teqzrtpgww`, 일회용 메일,
가입 1초 후 자동 로그인, 활동 없음) 가입을 **관리자 승인제**로 바꿨다.

- 가입 시 `is_active=False`로 만들고 `SignupApproval`(토큰) 생성 → 자동 로그인 없음
- 관리자(`ADMIN_NOTIFY_EMAIL`)에게 **승인/거부 링크**가 담긴 메일 발송
  - `/accounts/approve/<token>/`, `/accounts/reject/<token>/` — 로그인 불필요
- `/accounts/approvals/` 관리 페이지 (staff 전용). 신청자 IP·기기 정보로 봇 판별
- 승인되면 가입자에게 안내 메일 자동 발송
- **기존 사용자는 영향 없음** (승인 레코드가 없고 `is_active=True`)

주의: `LoginForm.confirm_login_allowed`는 **비활성 계정에서 호출되지 않는다.**
기본 `ModelBackend`가 인증 단계에서 먼저 거절하기 때문. 그래서 `clean()`에서
비밀번호를 직접 확인해 "승인 대기 중"을 안내한다. 이걸 놓치면 대기자에게
"아이디 또는 비밀번호가 올바르지 않습니다"가 나간다.

메일 본문의 절대 주소는 `settings.SITE_URL` 사용.

## 문제 풀이 화면의 공통 규칙 (2026-08-27)

기출·주제별·복습·오답노트(3종)·연습문제·용어 상세가 같은 모양을 쓴다.
한 곳을 고치면 나머지도 같이 고쳐야 어긋나지 않는다.

| 화면 | 파일 |
|---|---|
| 기출문제 | `study/templates/study/detail.html` |
| 주제별 문제 | `study/templates/study/topic_solve.html` |
| 오늘의 복습 | `templates/mypage/review_index.html` |
| 오답노트 | `templates/mypage/wrong_answer_list.html` |
| 기출시험 결과 | `templates/mypage/wrong_answer_full_list.html` |
| 오답 상세 | `templates/mypage/wrong_answer_detail.html` |
| 연습문제 | `practice/templates/practice/practice_questions.html` |
| 용어 상세 | `glossary/templates/glossary/term_detail.html` |

### 선지별 설명 (`choice_notes`)

- `Question.choice_notes` = `{"1": "설명", ...}` (JSONField). 1,045문항 전체 채움
- 화면 표시는 `choice_note` 필터 (`exam/templatetags/markdown_extras.py`)
- `↪` 화살표 + 정답 선지에만 노란 형광 띠 (`.hl`)
- 선지를 고르면 정답 표시·설명·관련 용어가 함께 나온다.
  아래 '해설 보기'는 따로 눌러야 펼쳐진다

### 용어 점선과 뜻 상자

- 사전에 있는 낱말에만 점선을 긋는다. 없는 말에 밑줄만 그으면 눌러도 보여 줄 게 없다
- 점선은 `radial-gradient`로 **작은 점을 촘촘히**(`2.5px 2px`) 깐다.
  `text-decoration: dotted`는 점이 붙어 실선처럼 뭉개진다
- **답을 고르기 전에는 선지의 점선을 감춘다**(`pointer-events: none`). 푸는 데 방해된다
- 누르면 그 선지 아래에 뜻이 펼쳐진다. 상자가 열리며 밀린 만큼
  스크롤을 되돌려 **누른 낱말이 제자리에 남게** 한다 (`keepInPlace`)

### 수식·학명 표기

데이터에 LaTeX가 섞여 들어온다. **화면에 그릴 때** 정리한다(DB는 그대로).

- `glossary/views.py`의 `_unwrap_plain_math()`가 처리
- 학명(`Genus species`, `\textit{...}`) → `<i>` **본문 글꼴** 이탤릭.
  수식 글꼴(세리프)로 그리면 주변 한글과 어긋난다
- 일반 낱말(`pH` `ATP` `Cellulose`) → 보통 글자
- 온도·단위·백분율(`$15^\circ\text{C}$`, `$5\%$`) → `15°C`, `5%`
- 진짜 수식(`$CO_2$` `$Ca^{2+}$` `$x$`)은 그대로 둔다
- 학명 판별을 넓히면 속명(`Clavibacter`)이 잘못 풀린다. 라틴어 어미와
  본문에서 `Genus species`로 쓰인 적이 있는지로 가린다

### 목록 들여쓰기

용어 설명이 `1.`(소제목) → `1)` → `-` 세 단계로 온다.

- 소제목이 없는 글은 `*`가 그냥 글머리표다. 번호를 매기면 빈 줄마다
  카운터가 돌아가 `1) 1) 1)`이 된다 → 소제목이 있을 때만 번호 (`glossary/views.py`)
- 넘어가는 줄은 글자 자리에 맞춘다(내어쓰기). `1) 정의:` 처럼 콜론이 있으면
  라벨 폭을 재서 그 뒤에 맞춘다 (grid, 라벨 14자 넘으면 건너뜀)
- `1.`이 마크다운 `<ol><li>`로 오는 글은 `<li>` 자체 들여쓰기가 이미 있어
  바깥 들여쓰기를 덜어내야 두 번 밀리지 않는다

### 미리보기 (`_plain_preview`, `mypage/views.py`)

나의 질의응답과 연습문제 상세의 관련 Q&A가 함께 쓴다.

- 본문이 모두 HTML이라 그냥 자르면 태그 한가운데가 잘려 깨진다.
  `<strong>`/`<em>`만 남기고 나머지는 글자로 만든 뒤 자른다
- 잘린 자리에서 태그 짝이 깨지면 열린 것을 닫고 짝 없는 닫는 태그는 버린다
- **소제목만 배지**(`핵심 개념` `상세 설명` 등), 나머지 굵게는 보통 글자로.
  본문 곳곳이 굵으면 무엇이 소제목인지 헷갈린다
- 학명(`Genus species`)의 기울임은 살린다

## 화면에서 되풀이해 어긋났던 것들

- **`margin-left`만 쓰면 앞 규칙의 `margin`이 통째로 덮인다.** `.bullet-item`에
  `margin: 3px 0`을 주고 `.bullet-level2`에 `margin-left`만 주면 위아래가
  기본값으로 돌아가 간격이 벌어진다. 상하까지 함께 적을 것
- **음수 여백으로 상자를 끌어올리면 글자가 겹친다.** 문단 중간 줄 아래에
  넣으려면 문단을 쪼개야 하는데 본문 HTML이 깨질 위험이 커서 하지 않는다
- **`target="_blank"`가 남아 있으면 `preventDefault()`가 소용없다.**
  그 자리에서 펼치려면 `target`을 지울 것
- **Django `{# #}`는 한 줄 주석이다.** 여러 줄로 쓰면 본문에 그대로 나온다
- **데코레이터와 함수 사이에 다른 함수를 끼워 넣지 말 것.** `@login_required`가
  엉뚱한 함수에 붙고 뷰는 데코레이터를 잃어 500이 난다
- MathJax는 `base.html`에만 있다. 이를 상속하지 않는 화면(복습·오답노트)에는
  따로 넣어야 `$4$월`처럼 달러가 글자로 보이지 않는다
- 나중에 불러오는 글(용어 뜻 등)은 `MathJax.typesetPromise([el])`로 다시 그려야 한다

## 알려진 주의사항

### content 필드의 HTML

- `Question.content`에 `<div style="border:...">` 등 HTML이 포함된 문제가 있음
- 목록/카드 미리보기에서는 `|striptags|truncatechars:N` 사용 (HTML 제거 후 자르기)
- `|safe|truncatechars:N`는 태그 중간에서 잘려 깨진 HTML이 렌더링되므로 금지
- 문제 상세 페이지에서만 `|safe` 사용

### 데이터 마이그레이션 (dumpdata/loaddata)

- `study/signals.py`의 `post_save` 시그널에 `raw` 체크가 있으므로 `loaddata` 안전
- dumpdata 시 `--natural-primary` 사용 금지 (auth.User PK 충돌)
- 권장 명령: `python manage.py dumpdata --natural-foreign --exclude=contenttypes --exclude=auth.permission --exclude=admin.logentry --indent=2`

### 나무주치의(챗봇) 오류 응답 처리

- `chat/views.py`의 `index()`와 `chat_api()`는 질문마다 BBS "주치의" 게시글을 자동 생성
- 2026-07-28 수정: `is_success`가 True일 때만 게시글 생성 (커밋 `c35480e`)
- 수정 전에는 API 오류 메시지가 그대로 게시글 본문이 되어 공개 게시판에 노출됨 (12건 삭제 완료)
- **사용자 화면에는 여전히 예외 원문이 표시됨** (`response_text = f"Error: {str(e)}"`). 사용자용 안내 문구로 교체하는 작업 미완료

### Gemini API 키 장애 이력

- 2026-06-25 ~ 2026-07-28: `GEMINI_API_KEY` 무효화(`API_KEY_INVALID`)로 챗봇 및 새벽 3시 크론이 약 한 달간 실패. 아무도 인지하지 못함
- 과거에도 유사 장애 반복: 2025-12-17 키 만료, 2025-12-19 모델명 오류(404), 2025-12~2026-02 할당량 초과(429)
- 키 상태 점검은 서버에서 실제 호출로 확인할 것 (로컬/서버 키 지문 비교 → 실제 API 호출)
- **모니터링 없음**: 크론 실패/챗봇 오류를 알리는 장치가 없어 장기 장애를 놓침

## 미결 과제 (2026-07-28 기준)

### 보안: Gmail 앱 비밀번호 노출 (우선순위 높음)

- `config/settings.py:140`의 `EMAIL_HOST_PASSWORD`가 평문 하드코딩 상태이며 Git에 커밋됨 (최초 커밋 `31d950a`)
- 원격 저장소 `github.com/gocompu21/03_1_model`에 포함 — 공개 저장소면 외부 노출
- 조치 필요:
  1. [Google 앱 비밀번호](https://myaccount.google.com/apppasswords)에서 폐기 후 재발급 (사용자 직접)
  2. `settings.py` 하드코딩 제거 → `.env`로 이동 (`.env`는 `.gitignore`에 포함되어 안전)
  3. 저장소 공개 여부 확인
- Gemini 키 무효화도 저장소 노출로 인한 Google 자동 회수 가능성 있음 (미확인)

### 장애 알림 메일 구성

- 서버에 MTA는 없으나 Gmail SMTP(587/465) 아웃바운드 열려 있고 Django `EMAIL_BACKEND` 설정 완료 → `send_mail()`로 발송 가능
- 감지 대상: 새벽 3시 크론(`refresh_file_store.py`) 실패, 챗봇 API 오류, 사이트 다운
- 주의: 429 오류는 짧은 시간에 수십 건 발생하므로 동일 유형 하루 1회 제한 필요
- 앱 비밀번호 교체 후 진행 예정

### 챗봇 429 할당량 초과

- `ChatHistory`에 실패 기록 46건 잔존, 그중 33건이 429 (분석용으로 보존)
- 주로 `jsj7007` 사용자가 짧은 간격으로 연속 질문할 때 발생 (2025-12-28 ~ 2026-02-03)
- 무료 등급 rate limit으로 추정. 유료 등급 확인 또는 재시도/요청 간격 제한 검토 필요

## 목차별 기본서·문제 만들기 (2026-08-29)

수목해충학 7.1.x(42개)와 7.2.x(60개)를 끝냈다. 7.3~7.5(27개)가 남았다.
`/dashboard/textbook/` 화면이 하는 일을 스크립트로 묶되 **확인은 사람이 한다**.

### 진행 현황

| 구간 | 상태 |
|---|---|
| 7.1.1 ~ 7.1.7 | 옛 방식 (선지별 설명 없음). 건드리지 않음 |
| 7.1.8 ~ 7.1.42 | **완료** 35개 |
| 7.2.1 ~ 7.2.60 | **완료** 60개 (2026-08-30) |
| 7.3 · 7.4 · 7.5 | 손대지 않음 27개 (id 585~611) |

DVD 해충 사진은 7.1.20 ~ 7.2.60 본문 맨 위에 넣었다
(`add_dvd_photo.py`, 확인은 `audit_dvd_photo.py`).
새 목차를 `apply.py` 로 저장한 뒤에는 `add_dvd_photo.py <id> --go` 도 함께 돌린다.
큰붉은잎밤나방·두충밤나방·주홍날개꽃매미는 pestid 에 같은 이름이 없어 빠졌다.

### 절차 (4개씩 묶어서)

스크립트는 `tools/chapter_gen/`에 있고 서버 `/tmp/`에도 같은 것이 있다.

```bash
# 1) 생성 — 본문·이미지·문제를 만들어 /tmp/prep/<id>.json 에만 둔다 (저장 안 함)
ssh ... "cd ~/myproject/03_1_model && rm -f /tmp/prep/*.json &&
         nohup ~/myproject/venv/bin/python /tmp/prep.py 553 554 555 556 > /tmp/prep.log 2>&1 &"
# 4개에 7~10분. pgrep -f prep.py 로 확인

# 2) 사람이 확인 — 이미지를 받아서 보고, 문제를 읽는다
scp ... ubuntu@studynamu.com:~/myproject/03_1_model/media/temp_infographics/textbook_<id>_*.jpg .

# 3) 손보기
python /tmp/more_prep.py <id> 5      # 문제가 5개 미만이면 채운다
python /tmp/fixmath.py <id들>        # $...$ 수식을 글자로
python /tmp/redo_img.py <id> "지시"  # 이미지에 틀린 글자가 있으면 다시

# 4) 저장 — 본문(이미지는 맨 위) + 문제 + 주제별 문제집
python /tmp/apply.py 553 554 555 556 --go
```

### 사람이 봐야만 잡히는 것들 (기계는 못 잡는다)

목차당 1~3건꼴로 나온다. 44개 목차에서 20건 넘게 잡았다.

- **이미지에 없는 낱말** — "곰나무" "볼리도루" "교육인보" "푼패시", 종명 오타
  (`redo_img.py` 로 다시. 지시는 영어로, 한글 예시를 넣으면 그 글자가 그림에 찍힌다)
- **설명이 엉뚱한 선지에 붙음** — 칸 수는 5개로 맞아 파서가 못 잡는다. 읽어야 보인다.
  뒤바뀐 것은 `swapnote.py <id> <문제번호> <선지a> <선지b>` 로 맞바꾼다
- **생활사 순환도 순서** — 산란 화살표가 알에서 나가거나, 부화가 산란보다 앞에 오거나,
  번데기 단계가 빠지거나, 같은 단계가 두 번 나온다. **단계를 하나씩 세어 가며
  본문과 대조할 것.** 20개 중 3개에서 나왔다
- **형태가 실물과 다름** — 사진을 함께 열어 대조한다. 7.2.42 소나무가루깍지벌레는
  본문이 "밀랍돌기가 짧다"인데 그림은 길고 뾰족하게 그렸고, 하필 그 목차 문제의
  정답이 그 내용이라 그림이 정답과 반대를 보여 주고 있었다
- **이미지 절 번호 뒤엉킴** — 2,1,4 처럼

기계가 잡는 것: 밀림(정답 설명 누락), 수식 찌꺼기, 문제 수 부족, 선지 번호 중복.

### 이미지 다시 만들기

- **최대 5번까지.** 재생성이 단조롭게 나아지지 않는다. 한 곳을 고치면 다른 곳이 깨진다.
  7.1.13 은 8번 돌렸는데 매번 다른 곳이 깨져 결국 방제 칸을 포기했다
- **판마다 파일명(timestamp)이 다르므로 이전 판을 버리지 말 것.** 나빠지면
  `/tmp/prep/<id>.json` 의 `image` 를 이전 파일명으로 되돌린다. 실제로 7.2.40 은
  4번째가 3번째보다 나빠 되돌렸다
- 자잘한 오타(알아볼 수 있는 한두 글자)는 통과시키고, 뜻 없는 문장이나 핵심 용어가
  깨진 것, 형태·생활사 오류만 재시도한다
- **이미 저장한 뒤에 잘못을 찾으면 `refix_img.py <id> "지시"`** — 본문의 `<img src>` 만
  갈아 끼운다 (`redo_img.py` 는 저장 전 prep 파일용)

### 되풀이해 어긋났던 것

- **문제집이 다른 해충 기출을 가져간다.** 이름이 더 긴 이름 안에 들어갈 때.
  '선녀벌레'로 찾으면 '미국선녀벌레' 문항이 잡힌다. 실제로 선녀벌레는 기출 0인데
  15문항짜리 문제집이 있었다. `apply.py`가 더 긴 이름을 지운 뒤 찾도록 고쳤고,
  `auditsets.py`로 전수 점검할 수 있다
- **모델이 정답 선지 설명을 빼고 오답 4개만 보낸다.** 그러면 정답 자리부터 뒤가
  한 칸씩 당겨진다. 파서가 이 경우를 버리고, `prep.py`가 선지별로 다시 묻는다
  (한 번에 다섯을 받으면 또 밀리므로 **하나씩** 물어야 한다)
- **본문에 없는 내용이 문제에 나오면 교과서와 대조할 것.** 대개 문제가 맞고
  본문이 부족한 것이다 (오리나무잎벌레 총 산란수 300개 등). 본문을 채워 준다
- 이미지는 **본문 맨 위**에, 다른 목차와 같은 마크업으로
  (`text-align:center; margin-bottom:20px` + `max-width:800px`)

### 기출 빈도 상위

매미나방 16, 미국선녀벌레·갈색날개매미충·오리나무잎벌레 15, 버즘나무방패벌레 14,
미국흰불나방 13, 솔나방 12, 황다리독나방 8, 목화진딧물·회양목명나방 7.
기출이 0인 목차는 문제집을 만들지 않는다.

## Korean Language Context

모든 UI와 데이터는 한국어. 과목 예시:
- 수목병리학 (Tree Pathology)
- 수목해충학 (Forest Entomology)
- 수목생리학 (Tree Physiology)
- 산림토양학 (Forest Soil Science)
- 수목관리학 (Tree Management)
- 농약학 (Pesticide Science)
