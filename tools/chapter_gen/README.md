# 목차별 기본서·문제 만들기

`/dashboard/textbook/` 화면이 하는 일을 스크립트로 묶은 것.
자세한 절차와 주의점은 저장소 루트 `CLAUDE.md` 의
"목차별 기본서·문제 만들기" 절을 볼 것.

서버 `/tmp/` 에 같은 파일이 있다. 고쳤으면 옮겨 두어야 한다.

```bash
scp -i "C:\AWS\myServer-key-pair.pem" tools/chapter_gen/*.py \
    ubuntu@studynamu.com:/tmp/
```

| 파일 | 하는 일 |
|---|---|
| `prep.py` | 본문·이미지·문제를 만들어 `/tmp/prep/<id>.json` 에 둔다 (저장 안 함) |
| `apply.py` | 확인이 끝난 것을 실제로 저장 (본문·문제·주제별 문제집) |
| `more_prep.py` | 문제가 5개에 못 미칠 때 더 만든다 |
| `fixmath.py` | 선지·설명에 남은 `$...$` 수식을 글자로 |
| `redo_img.py` | 이미지에 틀린 글자가 있을 때 다시 만든다 |
| `auditsets.py` | 문제집이 그 해충 기출만 담았는지 전수 점검 |
| `verify_all.py` | 만든 목차 전체를 훑어 빠진 곳 확인 |

`prep.py` 와 `apply.py` 는 목차 id 를 인자로 받는다.
`apply.py` 는 `--go` 를 붙여야 실제로 저장한다 (없으면 미리보기).
