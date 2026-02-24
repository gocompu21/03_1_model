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

## Korean Language Context

모든 UI와 데이터는 한국어. 과목 예시:
- 수목병리학 (Tree Pathology)
- 수목해충학 (Forest Entomology)
- 수목생리학 (Tree Physiology)
- 산림토양학 (Forest Soil Science)
- 수목관리학 (Tree Management)
- 농약학 (Pesticide Science)
