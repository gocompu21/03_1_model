# 이미 저장된 문제의 빈 선지별 설명(choice_notes)만 채운다. 문제·선지·정답·해설은
# 그대로 둔다. 7.1.1 ~ 7.1.5 처럼 옛 방식으로 만들어 선지 설명이 없는 목차용.
#   python fill_notes.py 483 484 ...        # 만들어 /tmp/notes/<id>.json 에만 둔다
#   python fill_notes.py 483 484 ... --go   # 그 파일을 읽어 DB 에 저장한다
#
# prep.py 의 ask_note 와 같이 선지를 하나씩 묻는다 (다섯을 한 번에 받으면 정답 설명이
# 빠지면서 뒤가 한 칸씩 밀린다). 기존 해설을 함께 넘겨 설명이 해설과 어긋나지 않게 한다.
import os, django, sys, json, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '/home/ubuntu/myproject/03_1_model')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from django.conf import settings
from practice.models import Chapter, PracticeQuestion
from glossary.views import _unwrap_plain_math

GO = '--go' in sys.argv
ids = [int(a) for a in sys.argv[1:] if a.isdigit()]
OUT = '/tmp/notes'
os.makedirs(OUT, exist_ok=True)
MARKS = '①②③④⑤'


def clean(t):
    t = re.sub(r'\$\\text\{([^{}]*)\}\$', lambda m: m.group(1), t)
    t = re.sub(r'\$([A-Za-z][A-Za-z \-]*)\$', lambda m: m.group(1), t)
    t = re.sub(r'\*+', '', t)
    return _unwrap_plain_math(t).strip()


def strip_html(t):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', t or '')).strip()


if GO:
    for cid in ids:
        d = json.load(open('%s/%d.json' % (OUT, cid), encoding='utf-8'))
        ch = Chapter.objects.get(id=cid)
        print('%s %s' % (ch.code, ch.title))
        for row in d['questions']:
            if len(row['choice_notes']) != 5:
                print('  %d번: 5칸이 아니라 건너뜀' % row['number']); continue
            q = PracticeQuestion.objects.get(id=row['id'])
            # 모델이 가끔 <i>학명</i> 태그나 $Genus\ species$ 수식 표기를 섞어 보낸다.
            # 다른 설명은 모두 맨글자이므로 글자로 푼다
            def plain(v):
                v = re.sub(r'<[^>]+>', '', v)
                # 첨자(^ _)가 없는 $...$ 는 진짜 수식이 아니다: $9\text{ mm}$, $Genus\ species$
                def unwrap(m):
                    s = m.group(1)
                    if re.search(r'[\^_]', s):
                        return m.group(0)
                    s = re.sub(r'\\text\{([^{}]*)\}', r'\1', s)
                    return s.replace('\\ ', ' ').replace('\\', '')
                v = re.sub(r'\$([^$]+)\$', unwrap, v)
                return re.sub(r'\s+', ' ', v).strip()
            q.choice_notes = {k: plain(v) for k, v in row['choice_notes'].items()}
            q.save(update_fields=['choice_notes'])
        print('  저장 %d문제' % sum(1 for r in d['questions'] if len(r['choice_notes']) == 5))
    raise SystemExit

from fileSearchStore import GeminiStoreManager
mgr = GeminiStoreManager(api_key=settings.GEMINI_API_KEY)
mgr.sync_all_stores()


def ask_note(ch, q, idx):
    ch_txt = '\n'.join('%s %s' % (MARKS[i], getattr(q, 'choice%d' % (i + 1))) for i in range(5))
    is_ans = (idx == q.answer)
    expl = strip_html(q.explanation)[:600]
    prompt = f'''{ch.code} {ch.title} 관련 문제입니다.

문제: {strip_html(q.content)}
{ch_txt}
정답: {q.answer}번
기존 해설: {expl}

{MARKS[idx-1]}번 선지 "{getattr(q, 'choice%d' % idx)}" 에 대한 설명만 한두 문장으로 써 주세요.
- 이 선지는 {'정답입니다. 왜 옳은지' if is_ans else '정답이 아닙니다. 왜 틀렸는지'}를 교과서 근거로 밝힙니다.
- 기존 해설과 어긋나지 않게 쓰되, 해설을 그대로 베끼지 말고 이 선지에 대해서만 씁니다.
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


for cid in ids:
    ch = Chapter.objects.select_related('book').get(id=cid)
    print('\n=== %s %s (id=%d)' % (ch.code, ch.title, cid), flush=True)
    rows = []
    for q in PracticeQuestion.objects.filter(chapter=ch).order_by('number'):
        notes = dict(q.choice_notes or {})
        if len(notes) == 5:
            print('  %d번: 이미 있음' % q.number, flush=True)
        else:
            notes = {}
            for i in range(1, 6):
                t = ask_note(ch, q, i)
                if t:
                    notes[str(i)] = t
            print('  %d번: %d칸%s' % (q.number, len(notes), '' if len(notes) == 5 else ' (못 채움)'),
                  flush=True)
        rows.append({'id': q.id, 'number': q.number, 'content': strip_html(q.content),
                     'choices': [getattr(q, 'choice%d' % i) for i in range(1, 6)],
                     'answer': q.answer, 'choice_notes': notes})
    json.dump({'chapter_id': cid, 'code': ch.code, 'title': ch.title, 'questions': rows},
              open('%s/%d.json' % (OUT, cid), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)
print('\n만든 것: %s' % ' '.join(str(i) for i in ids), flush=True)
