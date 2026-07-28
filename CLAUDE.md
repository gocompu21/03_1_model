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

## Korean Language Context

모든 UI와 데이터는 한국어. 과목 예시:
- 수목병리학 (Tree Pathology)
- 수목해충학 (Forest Entomology)
- 수목생리학 (Tree Physiology)
- 산림토양학 (Forest Soil Science)
- 수목관리학 (Tree Management)
- 농약학 (Pesticide Science)
