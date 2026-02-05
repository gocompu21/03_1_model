# HANDOFF.md - 작업 인수인계 문서

## 프로젝트 개요
나무의사 자격시험 학습 플랫폼의 모바일 반응형 디자인 개선 작업

---

## 완료된 작업 (이전 세션)

### 1. Dashboard 모바일 카드 레이아웃 (완료)
### 2. Dashboard 정렬 로직 (완료)
### 3. 마이페이지 전체 오답 노트 PC 버전 (완료)
### 4. 마이페이지 전체 오답 노트 모바일 버전 (완료)

*(상세 내용은 이전 버전 참고)*

---

## 완료된 작업 (2026-02-05 세션)

### 5. 전체 오답 노트 무한 스크롤 (완료)
**파일**:
- `templates/mypage/wrong_answer_partial.html`
- `templates/mypage/index.html`

**구현 내용**:
- 페이지네이션 UI 제거 → 무한 스크롤로 변경
- 스크롤 하단 100px 도달 시 다음 15개 항목 자동 로드
- 로딩 인디케이터 표시

**핵심 코드** (`wrong_answer_partial.html`):
```html
<div id="wrong-answer-scroll-data"
     data-page="{{ wrong_answers.number }}"
     data-has-next="{{ wrong_answers.has_next|yesno:'true,false' }}"
     data-next-page="{{ wrong_answers.next_page_number|default:'' }}">
</div>
```

**JS 위치**: `index.html` 라인 1919-2091 (`initWrongAnswerInfiniteScroll`)

---

### 6. 이미지 클릭 모달 (Lightbox) (완료)
**파일**: `templates/mypage/index.html`, `templates/mypage/wrong_answer_detail.html`

**구현 내용**:
- 문제 이미지, 인포그래픽 이미지 클릭 시 전체화면 모달
- 모바일: 핀치 줌, 더블탭 확대/축소
- PC: 마우스 휠 줌
- 닫기: X 버튼, 배경 클릭, ESC 키

**CSS 위치**: `index.html` 라인 1070-1135 (`.lightbox-*` 클래스)
**HTML 위치**: `index.html` `</body>` 바로 앞 (`<div class="lightbox-overlay">`)
**JS 위치**: `index.html` 맨 마지막 `<script>` (`window.openModal` 함수)

**이미지 onclick**:
```html
<img onclick="openModal(this.src)">
```

---

### 7. 브라우저 뒤로가기 처리 (완료)
**파일**: `templates/mypage/index.html`

**구현 내용**:
- 오답 상세 진입 시 `history.pushState` 호출
- `popstate` 이벤트에서 상세 화면 열려있으면 리스트로 복원
- 리스트에서 뒤로가기 시 메인으로 이동 (브라우저 기본 동작)

**핵심 코드**:
```javascript
// loadWrongAnswerDetail 함수 내
history.pushState({ view: 'wrong_answer_detail', id: id }, '', url);

// popstate 핸들러
window.addEventListener('popstate', function(e) {
    const detailView = document.getElementById('wrong-answer-detail-view');
    if (detailView && detailView.style.display !== 'none') {
        showWrongAnswerList();
    }
});
```

**JS 위치**: `index.html` 라인 3623-3632

---

### 8. 가독성 개선 (완료)
**파일**: `templates/mypage/index.html`

**변경 내용 (768px 이하)**:
| 요소 | 변경 전 | 변경 후 |
|------|---------|---------|
| 문제 (td:nth-child(3)) | 0.9rem, 3줄 제한 | **1rem, 전체 표시** |
| 과목 (td:nth-child(2)) | 0.75rem | **0.8rem** |
| 응시일시 (td:nth-child(1)) | 0.7rem | **0.8rem** |
| 카드 패딩 | 12px | **14px** |

**CSS 위치**: 라인 901-938

---

### 9. 카드 레이아웃 변경 (완료)
**파일**: `templates/mypage/index.html`

**현재 레이아웃**:
```
┌─────────────────────────────────────┐
│ 15-3. 문제 내용 전체 표시...          │
├─────────────────────────────────────┤
│                    26/01/01 18:41 [산림토양학] │
└─────────────────────────────────────┘
```

**CSS 핵심**:
```css
/* 응시일시 (하단 오른쪽 - 먼저) */
.history-table td:nth-child(1) { order: 2; margin-left: auto; }
/* 과목 (하단 오른쪽 - 응시일시 뒤) */
.history-table td:nth-child(2) { order: 3; margin-left: 8px; }
```

---

### 10. HTML 태그 렌더링 (완료)
**파일**: `templates/mypage/wrong_answer_partial.html`

**문제**: `<div>` 태그가 텍스트로 노출됨
**해결**: `{{ result.question.content|safe }}` 필터 추가

---

### 11. 폰트 스타일 통일 (완료)
**파일**: `templates/mypage/wrong_answer_detail.html`

**변경 내용** (study/detail.html과 동일하게):
| 요소 | 변경 전 | 변경 후 |
|------|---------|---------|
| .q-content | 1.15em | **1.2em** |
| .choice-item | padding 8px | **padding 10px, line-height 1.5** |
| .markdown-content | - | **line-height 1.8, font-size 1.05em** |

**모바일 반응형 추가** (768px 이하):
```css
.q-content { font-size: 1rem; }
.choice-item { font-size: 1rem; }
.markdown-content { font-size: 1rem; }
```

---

## 발생했던 문제와 해결

| 문제 | 원인 | 해결 |
|------|------|------|
| 이미지 클릭 안됨 | Lightbox HTML이 script 뒤에 배치 | HTML을 script 앞으로 이동, JS를 별도 script로 분리 |
| 뒤로가기 시 메인으로 안감 | `replaceState`가 원래 히스토리 덮어씀 | 초기 `replaceState` 제거 |
| 상세→리스트 뒤로가기 안됨 | `popstate`에서 state 체크만 함 | 상세 화면 display 상태로 판단하도록 변경 |
| HTML 태그 노출 | `|safe` 필터 누락 | 필터 추가 |

---

## 관련 파일 목록

```
templates/mypage/
├── index.html                  # 마이페이지 메인
│   ├── CSS: 모바일 .history-table 스타일 (라인 880-938)
│   ├── CSS: Lightbox 스타일 (라인 1070-1135)
│   ├── JS: 무한 스크롤 (라인 1919-2091)
│   ├── JS: loadWrongAnswerDetail (라인 2093-2143)
│   ├── JS: Lightbox (마지막 script)
│   └── JS: popstate 핸들러 (라인 3623-3632)
├── wrong_answer_partial.html   # 오답 리스트 (무한 스크롤 데이터)
└── wrong_answer_detail.html    # 오답 상세 (폰트 스타일, 이미지 onclick)
```

---

## 테스트 URL

- 마이페이지: `http://localhost:8000/mypage/`
- 전체 오답 노트: `http://localhost:8000/mypage/?section=wrong_answer`
- 비교용 학습 페이지: `http://localhost:8000/study/5`

---

## 테스트 체크리스트

- [ ] 전체 오답 노트 무한 스크롤 동작
- [ ] 오답 상세 이미지 클릭 → 모달 열림
- [ ] 모달 핀치 줌/더블탭/휠 줌 동작
- [ ] 오답 상세 → 뒤로가기 → 리스트 복원
- [ ] 리스트 → 뒤로가기 → 메인으로 이동
- [ ] 문제 내용 전체 표시 (3줄 제한 해제)
- [ ] HTML 태그 렌더링 (`<div>` 등)

---

## 다음 작업 제안

현재 요청된 작업은 모두 완료됨. 추가 요청 대기 중.

---

*마지막 업데이트: 2026-02-05*
