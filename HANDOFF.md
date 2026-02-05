# HANDOFF.md - 작업 인수인계 문서

## 프로젝트 개요
나무의사 자격시험 학습 플랫폼의 모바일 반응형 디자인 개선 작업

---

## 완료된 작업

### 1. Dashboard 모바일 카드 레이아웃 (완료)
**파일**: `dashboard/templates/dashboard/index.html`

**최종 레이아웃**:
- 1행: 상태 | 이름 | 기기 | 활동내용
- 2행: 기출 | 복습 | 오늘 | 누적

**CSS 위치**: 라인 377-488 (`@media screen and (max-width: 768px)`)

```css
.data-table tbody tr {
    display: grid;
    grid-template-columns: auto auto 1fr auto;
    grid-template-rows: auto auto;
    gap: 5px 8px;
}
```

**해결한 이슈**:
- 상태 컬럼("접속"/"부재") 너비 차이로 인한 정렬 문제 → `min-width: 45px` 추가

---

### 2. Dashboard 정렬 로직 (완료)
**파일**: `dashboard/views.py`

**정렬 우선순위**:
1. 접속 중인 사용자 우선
2. 오늘 사용시간 내림차순
3. 누적 사용시간 내림차순

```python
user_stats.sort(key=lambda x: (
    not x['is_online'],
    -x['today_minutes_raw'],
    -x['total_minutes_raw']
))
```

**추가된 필드**: `today_minutes_raw`, `total_minutes_raw` (정렬용 raw 값)

---

### 3. 마이페이지 전체 오답 노트 PC 버전 (완료)
**파일**: `templates/mypage/index.html`, `templates/mypage/wrong_answer_partial.html`

**변경사항**:
- 안내 문구 삭제 ("클릭하면 해당 문제의 상세 해설을 볼 수 있습니다.")
- "문제번호" 컬럼 삭제 → 3개 컬럼만 유지 (응시 일시, 과목, 문제)
- 문제 컬럼에 회차-번호 prefix 포함 (`15-3. 문제내용...`)

**현재 테이블 구조** (`wrong_answer_partial.html`):
```html
<th>응시 일시</th>
<th>과목</th>
<th>문제</th>
```

---

### 4. 마이페이지 전체 오답 노트 모바일 버전 (완료)
**파일**: `templates/mypage/index.html`

**CSS 위치**: 라인 864-940 (`.history-table` 모바일 스타일)

**카드 레이아웃**:
```
┌─────────────────────────────────────┐
│ 15-3. 문제 내용...                    │  ← nth-child(3): 상단, 3줄 제한
├─────────────────────────────────────┤
│ [수목병리학]               24/12/25 14:30 │  ← nth-child(2): 녹색배지 / nth-child(1): 회색
└─────────────────────────────────────┘
```

**CSS 핵심**:
```css
/* 문제 (상단) */
.history-table td:nth-child(3) { order: 1; width: 100%; }
/* 과목 (하단 왼쪽, 녹색 배지) */
.history-table td:nth-child(2) { order: 2; background: #e6f4ea; }
/* 응시일시 (하단 오른쪽) */
.history-table td:nth-child(1) { order: 3; margin-left: auto; }
```

---

## 발생했던 문제와 해결

| 문제 | 원인 | 해결 |
|------|------|------|
| 카드 정렬 불일치 (김상현 들여쓰기) | "접속"/"부재" 텍스트 너비 차이 | `min-width: 45px` 적용 |
| nth-child 인덱스 오류 | 테이블 컬럼 수 변경 후 CSS 미수정 | 3개 컬럼 구조에 맞게 nth-child(1,2,3) 재매핑 |
| 파일 미읽기 오류 | Edit 전 Read 미실행 | Read 후 Edit 순서 준수 |

---

## 관련 파일 목록

```
dashboard/
├── templates/dashboard/index.html  # 대시보드 (모바일 카드 레이아웃)
└── views.py                        # 정렬 로직

templates/mypage/
├── index.html                      # 마이페이지 메인 (모바일 CSS 포함)
├── wrong_answer_partial.html       # 오답 목록 테이블 (AJAX 로드)
└── wrong_answer_full_list.html     # 회차별 오답 상세 (별도 페이지)
```

---

## 테스트 URL

- 대시보드: `http://localhost:8000/dashboard/`
- 마이페이지: `http://localhost:8000/mypage/`
- 전체 오답 노트: 마이페이지 내 "전체 오답 노트" 섹션

---

## 다음 작업 제안

현재 요청된 작업은 모두 완료됨. 추가 요청 대기 중.

---

*마지막 업데이트: 2026-02-05*
