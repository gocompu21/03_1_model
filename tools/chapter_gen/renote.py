# fill_notes.py 가 만든 /tmp/notes/<id>.json 에서 선지 설명 한 칸만 다시 묻는다.
#   python renote.py <목차id> <문제번호> <선지번호> ["덧붙일 지시"]
# 정답 설명이 다른 선지 설명으로 붙었거나, 선지 내용과 무관한 설명이 왔을 때 쓴다.
import os, django, sys, json, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '/home/ubuntu/myproject/03_1_model')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from django.conf import settings
from practice.models import Chapter
from glossary.views import _unwrap_plain_math
from fileSearchStore import GeminiStoreManager

cid, qnum, idx = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
extra = sys.argv[4] if len(sys.argv) > 4 else ''
path = '/tmp/notes/%d.json' % cid
d = json.load(open(path, encoding='utf-8'))
ch = Chapter.objects.select_related('book').get(id=cid)
q = next(r for r in d['questions'] if r['number'] == qnum)
MARKS = '①②③④⑤'


def clean(t):
    t = re.sub(r'\$\\text\{([^{}]*)\}\$', lambda m: m.group(1), t)
    t = re.sub(r'\$([A-Za-z][A-Za-z \-]*)\$', lambda m: m.group(1), t)
    t = re.sub(r'\*+', '', t)
    t = re.sub(r'<[^>]+>', '', t)
    return _unwrap_plain_math(t).strip()


mgr = GeminiStoreManager(api_key=settings.GEMINI_API_KEY)
mgr.sync_all_stores()

ch_txt = '\n'.join('%s %s' % (MARKS[i], q['choices'][i]) for i in range(5))
is_ans = (idx == q['answer'])
prompt = f'''{ch.code} {ch.title} 관련 문제입니다.

문제: {q['content']}
{ch_txt}
정답: {q['answer']}번

{MARKS[idx-1]}번 선지 "{q['choices'][idx-1]}" 에 대한 설명만 한두 문장으로 써 주세요.
- 이 선지는 {'정답입니다. 왜 옳은지' if is_ans else '정답이 아닙니다. 왜 틀렸는지'}를 교과서 근거로 밝힙니다.
- 반드시 {MARKS[idx-1]}번 선지의 내용("{q['choices'][idx-1]}")에 대해서만 씁니다. 다른 선지를 언급하지 마세요.
- 근거가 되는 시기·수치·이름을 빠뜨리지 마세요.
- 교과서에 없는 수치를 지어내지 마세요.
- 다른 말 없이 설명 문장만 출력하세요. 번호나 굵게(**) 표기는 쓰지 마세요.
{extra}'''

print('%s %s [%d] %s' % (ch.code, ch.title, qnum, q['content']))
print('  %s %s' % (MARKS[idx-1], q['choices'][idx-1]))
print('  전: %s' % q['choice_notes'].get(str(idx), '(없음)'))
out = ''
for _ in range(3):
    raw = mgr.query_store(ch.book.subject, prompt).strip()
    for line in raw.split('\n'):
        line = re.sub(r'^\s*(?:정답\s*[:：]?\s*)?[①-⑤1-5]?\s*[번\).:：]*\s*', '', line.strip())
        line = clean(line)
        if len(line) > 20 and not line.isdigit():
            out = line
            break
    if out:
        break
if not out:
    raise SystemExit('  못 받았습니다')
q['choice_notes'][str(idx)] = out
json.dump(d, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('  후: %s' % out)
