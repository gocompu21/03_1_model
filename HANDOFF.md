# HANDOFF.md - 작업 인수인계 문서

## 프로젝트 개요
나무의사 자격시험 학습 플랫폼의 모바일 반응형 디자인 개선 작업

---

## 완료된 작업 (이전 세션)

### 1-11. 이전 작업들 (완료)
- Dashboard 모바일 카드 레이아웃
- Dashboard 정렬 로직
- 마이페이지 전체 오답 노트 PC/모바일 버전
- 전체 오답 노트 무한 스크롤
- 이미지 클릭 모달 (Lightbox)
- 브라우저 뒤로가기 처리
- 가독성 개선, 카드 레이아웃 변경
- HTML 태그 렌더링, 폰트 스타일 통일

---

## 완료된 작업 (2026-02-05 세션 2)

### 12. 카드 레이아웃 두번째 줄 컴팩트화 (완료)
**파일**: `templates/mypage/index.html` (라인 920-938)

**변경 내용**:
| 요소 | 변경 전 | 변경 후 |
|------|---------|---------|
| 문제↔하단 간격 | 10px + 10px | **6px + 6px** |
| 응시일시 폰트 | 0.8rem | **0.75rem** |
| 과목 폰트 | 0.8rem | **0.75rem** |
| 과목 배지 패딩 | 4px 10px | **1px 6px** |
| line-height | (기본) | **응시일시: 1, 과목: 1.2** |

---

### 13. 마크다운 이탤릭 렌더링 (완료)
**파일**: `exam/templatetags/markdown_extras.py` (라인 34-37)

**구현 내용**:
- 학명 등 `*텍스트*` → `<em>텍스트</em>` 변환 추가
- 볼드 처리 후 이탤릭 처리 (충돌 방지)
- 엄격한 정규식: 비공백 시작/끝, 최대 50자

**핵심 코드**:
```python
# 이탤릭: 비공백으로 시작/끝, 최대 50자
text = re.sub(r'\*(\S[^\*\n]{0,48}?\S|\S)\*', r'<em>\1</em>', text)
```

**주의**: `@lru_cache`가 적용되어 있어 서버 재시작 필요

---

### 14. 오답 상세 해설 영역 분리 (완료)
**파일**: `templates/mypage/wrong_answer_detail.html` (라인 83-87)

**변경 내용**:
- `.explanation-section` 박스 스타일 제거
- 상단 구분선으로 문제/해설 분리

```css
.explanation-section {
    padding-top: 24px;
    margin-top: 24px;
    border-top: 1px solid #e0e0e0;
}
```

---

### 15. MathJax 스타일 추가 (완료)
**파일**: `templates/mypage/wrong_answer_detail.html` (라인 52-72)

**구현 내용**:
- 인라인 수식 크기를 주변 텍스트와 동일하게
- notebook/index.html 스타일 참조

```css
.markdown-content .MathJax { font-size: 1.0em !important; }
.markdown-content mjx-container[jax="CHTML"] { font-size: inherit !important; }
.markdown-content mjx-math { font-size: inherit !important; }
```

---

### 16. 이어지는 오답 노트 무한 스크롤 + 카드 레이아웃 (완료)
**파일**:
- `templates/mypage/wrong_answer_detail.html` (라인 207-257)
- `mypage/views.py` (`next_wrong_answers_api` 함수)
- `mypage/urls.py` (라인 18-22)
- `templates/mypage/index.html` (JS: `initNextWrongAnswersScroll`, `loadMoreNextWrongAnswers`)

**구현 내용**:
1. HTML 구조를 전체 오답 리스트와 동일하게 변경 (3컬럼)
2. 백엔드 API 추가: `/mypage/api/next_wrong_answers/<pk>/?offset=10`
3. IntersectionObserver로 스크롤 감지
4. 10개씩 추가 로드

**핵심 코드** (views.py):
```python
@login_required
def next_wrong_answers_api(request, pk):
    result = get_object_or_404(UserQuestionResult, pk=pk, attempt__user=request.user)
    offset = int(request.GET.get("offset", 0))
    # ... 다음 10개 로드
    return JsonResponse({"items": items, "has_more": has_more, "offset": offset + limit})
```

---

### 17. 이어지는 오답 노트 영역 분리 (완료)
**파일**: `templates/mypage/wrong_answer_detail.html` (라인 207-209)

**변경 내용**:
- `wa-detail-container` 밖으로 분리
- 박스 스타일 제거 (배경, 테두리 없음)
- "목록으로" 버튼 → 아이콘만 (`<i class="fas fa-list">`)

---

### 18. 오늘의 복습 페이지 분리 (완료)
**파일**:
- `templates/mypage/review_index.html` (새 파일)
- `mypage/views.py` (`review_index` 함수, 라인 710-728)
- `mypage/urls.py` (라인 40)
- `templates/mypage/index.html` (메뉴 링크 변경, review-section 제거)

**구현 내용**:
1. 독립 페이지로 복습 기능 분리
2. 복습 카운트 요약, 카드 리스트, 복습 시작 버튼
3. 마이페이지 메뉴에서 별도 페이지 링크로 변경
4. 기존 `review-section` 제거

**URL**: `/mypage/review/`

**메뉴 변경**:
```html
<!-- 변경 전 -->
<div class="menu-item" onclick="showSection('review')">

<!-- 변경 후 -->
<a href="{% url 'mypage:review_index' %}" class="menu-item">
```

---

## 시도했으나 롤백한 작업

### 문제/해설 영역 박스 분리
- **시도**: `.question-section` 클래스로 문제 영역 별도 박스화
- **결과**: 사용자 요청으로 복구
- **최종**: 해설 영역만 구분선으로 분리

---

## 발생했던 문제와 해결

| 문제 | 원인 | 해결 |
|------|------|------|
| 이탤릭이 잘못된 곳에 적용 | 느슨한 정규식 `[^\*\n]+` | 엄격한 정규식 `\S[^\*\n]{0,48}?\S` |
| showSection 메뉴 인덱스 오류 | review 메뉴가 링크로 변경됨 | `menuItems` 선택자를 `div`만 선택하도록 변경 |

---

## 관련 파일 목록

```
templates/mypage/
├── index.html                  # 마이페이지 메인
│   ├── CSS: 모바일 .history-table 스타일 (라인 880-938)
│   ├── CSS: Lightbox 스타일 (라인 1070-1135)
│   ├── JS: 무한 스크롤 (라인 1919-2091)
│   ├── JS: loadWrongAnswerDetail (라인 2098+)
│   ├── JS: initNextWrongAnswersScroll, loadMoreNextWrongAnswers
│   └── JS: showSection (review case 제거됨)
├── wrong_answer_partial.html   # 오답 리스트 (무한 스크롤 데이터)
├── wrong_answer_detail.html    # 오답 상세
│   ├── CSS: MathJax 스타일 (라인 52-72)
│   ├── CSS: .explanation-section (라인 83-87)
│   └── HTML: 이어지는 오답 노트 (라인 207-257)
└── review_index.html           # 오늘의 복습 (독립 페이지, 새 파일)

mypage/
├── views.py
│   ├── review_index (라인 710-728)
│   └── next_wrong_answers_api (라인 442-477)
└── urls.py
    ├── review/ (라인 40)
    └── api/next_wrong_answers/<pk>/ (라인 18-22)

exam/templatetags/
└── markdown_extras.py          # 마크다운 필터 (이탤릭 추가, 라인 34-37)
```

---

## 테스트 URL

- 마이페이지: `http://localhost:8000/mypage/`
- 전체 오답 노트: `http://localhost:8000/mypage/?section=wrong_answer`
- 오답 상세: `http://localhost:8000/mypage/?section=wrong_answer&detail=1609`
- 오늘의 복습: `http://localhost:8000/mypage/review/`
- 비교용 학습 페이지: `http://localhost:8000/study/5`

---

## 테스트 체크리스트

- [ ] 전체 오답 노트 무한 스크롤 동작
- [ ] 오답 상세 이미지 클릭 → 모달 열림
- [ ] 오답 상세 → 뒤로가기 → 리스트 복원
- [ ] 이어지는 오답 노트 무한 스크롤 동작
- [ ] 이어지는 오답 노트 카드 클릭 → 상세 이동
- [ ] 학명 이탤릭 렌더링 (`*Exobasidium*` → *Exobasidium*)
- [ ] MathJax 수식 크기가 주변 텍스트와 동일
- [ ] 오늘의 복습 페이지 접속 가능
- [ ] 마이페이지 메뉴에서 오늘의 복습 클릭 → 별도 페이지 이동

---

## 알려진 이슈

1. **마크다운 캐시**: `@lru_cache` 때문에 마크다운 변경 후 서버 재시작 필요
2. **이탤릭 정규식 제한**: 50자 초과 또는 공백으로 시작/끝나는 패턴은 이탤릭 안 됨

---

## 다음 작업 제안

현재 요청된 작업은 모두 완료됨. 추가 요청 대기 중.

---

*마지막 업데이트: 2026-02-05*
