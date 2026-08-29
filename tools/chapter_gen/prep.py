# 여러 목차의 본문·이미지·문제를 미리 만들어 파일로만 남긴다. (저장은 하지 않음)
# 만든 것을 사람이 보고 확인한 뒤 apply.py 로 저장한다.
import os, django, sys, json, re, time
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '/home/ubuntu/myproject/03_1_model')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from django.conf import settings
from django.test import Client
from django.contrib.auth.models import User
from practice.models import Chapter
from fileSearchStore import GeminiStoreManager
from glossary.views import _unwrap_plain_math

CHS = [int(x) for x in sys.argv[1:] if x.isdigit()]
assert CHS, '목차 id 를 넘겨 주세요'
OUT = '/tmp/prep'
os.makedirs(OUT, exist_ok=True)

u = User.objects.filter(is_staff=True, is_superuser=True).first()
c = Client()
c.force_login(u)
mgr = GeminiStoreManager(api_key=settings.GEMINI_API_KEY)
mgr.sync_all_stores()
MARKS = '①②③④⑤'


def post(url, payload):
    r = c.post(url, data=json.dumps(payload), content_type='application/json')
    d = r.json()
    if not d.get('success'):
        raise RuntimeError('%s -> %s' % (url, d.get('error')))
    return d


def fix_section_numbers(html):
    pat = re.compile(r'(<span style="font-weight:bold; color:#2b6cb0[^"]*">)\((\d)\)(</span>)')
    n = [0]

    def rep(m):
        n[0] += 1
        return '%s(%d)%s' % (m.group(1), n[0], m.group(3))
    return pat.sub(rep, html)


def clean(t):
    t = re.sub(r'\$\\text\{([^{}]*)\}\$', lambda m: m.group(1), t)
    t = re.sub(r'\$([A-Za-z][A-Za-z \-]*)\$', lambda m: m.group(1), t)
    t = re.sub(r'\*+', '', t)
    return _unwrap_plain_math(t).strip()


def ask_note(ch, q, idx):
    ch_txt = '\n'.join('%s %s' % (MARKS[i], q['choice%d' % (i + 1)]) for i in range(5))
    is_ans = (idx == int(q['answer']))
    prompt = f'''{ch.code} {ch.title} 관련 문제입니다.

문제: {q['content']}
{ch_txt}
정답: {q['answer']}번

{MARKS[idx-1]}번 선지 "{q['choice%d' % idx]}" 에 대한 설명만 한두 문장으로 써 주세요.
- 이 선지는 {'정답입니다. 왜 옳은지' if is_ans else '정답이 아닙니다. 왜 틀렸는지'}를 교과서 근거로 밝힙니다.
- 근거가 되는 시기·수치·이름을 빠뜨리지 마세요.
- 교과서에 없는 수치를 지어내지 마세요.
- 다른 말 없이 설명 문장만 출력하세요. 번호나 굵게(**) 표기는 쓰지 마세요.'''
    for _ in range(3):
        raw = mgr.query_store(ch.book.subject, prompt).strip()
        for line in raw.split('\n'):
            line = re.sub(r'^\s*(?:정답\s*[:：]?\s*)?[①-⑤1-5]?\s*[번\).:：]*\s*', '',
                          line.strip())
            line = clean(line)
            if len(line) > 20 and not line.isdigit():
                return line
    return ''


def one(cid):
    ch = Chapter.objects.select_related('book').get(id=cid)
    print('\n=== %s %s (id=%d)' % (ch.code, ch.title, cid))

    html = fix_section_numbers(post('/dashboard/api/textbook/content/',
                                    {'chapter_id': cid})['content'])
    ctx = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html)).strip()[:1000]
    img = post('/dashboard/api/textbook/image/',
               {'chapter_id': cid, 'context': ctx}).get('image_url', '')

    d = post('/dashboard/api/textbook/quiz/', {'chapter_id': cid})
    qs = d.get('questions', [])
    warns = list(d.get('missing_notes', []))
    for q in qs:
        notes = {k: clean(v) for k, v in (q.get('choice_notes') or {}).items()}
        if len(notes) < 5:
            made = {}
            for i in range(1, 6):
                t = ask_note(ch, q, i)
                if t:
                    made[str(i)] = t
            if len(made) == 5:
                notes = made
                warns.append('%s번: 선지별로 다시 만들어 채움' % q['number'])
            else:
                warns.append('%s번: 못 채움(%d칸)' % (q['number'], len(made)))
        q['choice_notes'] = notes

    json.dump({'chapter_id': cid, 'code': ch.code, 'title': ch.title,
               'content': html, 'image': img, 'questions': qs, 'warns': warns},
              open('%s/%d.json' % (OUT, cid), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)
    print('  본문 %d자 / 이미지 %s / 문제 %d개 (5칸 %d개)'
          % (len(html), img.split('/')[-1], len(qs),
             sum(1 for q in qs if len(q['choice_notes']) == 5)))
    for w in warns:
        print('  [경고] %s' % w)


for cid in CHS:
    for a in range(2):
        try:
            one(cid)
            break
        except Exception as e:
            print('  !! %s (%d번째)' % (e, a + 1))
            time.sleep(5)
print('\n만든 것: %s/  (아직 저장 안 함)' % OUT)
