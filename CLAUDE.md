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

### Database
- SQLite (db.sqlite3). 백업 파일들 (db.sqlite3.MMDDHHMI 형식)

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

## Git Conventions

- 커밋 메시지는 **한글**로 작성
- 예시: `성능 개선: 용어 매칭 AJAX 지연 로딩 구현`

## Korean Language Context

모든 UI와 데이터는 한국어. 과목 예시:
- 수목병리학 (Tree Pathology)
- 수목해충학 (Forest Entomology)
- 수목생리학 (Tree Physiology)
- 산림토양학 (Forest Soil Science)
- 수목관리학 (Tree Management)
- 농약학 (Pesticide Science)
