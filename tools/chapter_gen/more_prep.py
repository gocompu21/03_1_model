# prep 로 만들어 둔 목차에 문제를 더 붙인다 (5개가 안 될 때).
#   python more_prep.py <목차id> [목표개수]
import os, django, sys, json, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '/home/ubuntu/myproject/03_1_model')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from django.conf import settings
from practice.models import Chapter
from fileSearchStore import GeminiStoreManager
from glossary.views import _unwrap_plain_math

cid = int(sys.argv[1])
want = int(sys.argv[2]) if len(sys.argv) > 2 else 5
p = '/tmp/prep/%d.json' % cid
d = json.load(open(p, encoding='utf-8'))
qs = d['questions']
need = want - len(qs)
print('%s %s — 지금 %d문제, %d개 더' % (d['code'], d['title'], len(qs), need))
if need <= 0:
    raise SystemExit

ch = Chapter.objects.select_related('book').get(id=cid)
mgr = GeminiStoreManager(api_key=settings.GEMINI_API_KEY)
mgr.sync_all_stores()


def clean(t):
    t = re.sub(r'\$\\text\{([^{}]*)\}\$', lambda m: m.group(1), t)
    t = re.sub(r'\$([A-Za-z][A-Za-z \-]*)\$', lambda m: m.group(1), t)
    t = re.sub(r'\*+', '', t)
    t = re.sub(r'^\s*\d+\.\s*', '', t)
    return _unwrap_plain_math(t).strip()


already = '\n'.join('- %s' % q['content'] for q in qs)
prompt = f'''{ch.code} {ch.title}에 대한 내용 이해 문제를 5지선다형으로 {need}개 더 출제해 주세요.

아래 문제는 이미 냈으니 겹치지 않는 다른 내용으로 내 주세요.
{already}

탭(tab)으로 나눈 한 줄에 아래 순서대로 담아 주세요. 한 문제당 한 줄입니다.

문제번호\t문제\t보기1\t보기2\t보기3\t보기4\t보기5\t정답\t해설\t선지1설명\t선지2설명\t선지3설명\t선지4설명\t선지5설명

한 줄은 반드시 탭 13개로 나뉜 14칸이어야 합니다.
특히 정답 선지의 설명을 빠뜨리지 마세요. 정답이 3번이면 '선지3설명' 칸에도 내용이 들어가야 합니다.

- 다섯 선지 모두에 설명을 답니다.
- 각 설명은 반드시 그 번호의 선지에 대한 것이어야 합니다.
- 교과서에 없는 수치를 지어내지 마세요.
- 선지 앞에 번호를 다시 쓰지 마세요. 굵게(**) 표기도 쓰지 마세요.'''

raw = mgr.query_store(ch.book.subject, prompt)
start = max(int(q['number']) for q in qs) + 1
added = 0
for line in raw.strip().split('\n'):
    parts = line.split('\t')
    if len(parts) < 8 or parts[0].strip() == '문제번호':
        continue
    try:
        ans = int(parts[7].strip())
    except ValueError:
        continue
    notes = {}
    for i in range(5):
        col = 9 + i
        v = clean(parts[col].strip()) if len(parts) > col else ''
        if v and not v.isdigit() and len(v) >= 10:
            notes[str(i + 1)] = v
    if len(notes) == 4 and str(ans) in notes:
        print('  (밀린 줄 하나 버림)')
        continue
    if len(notes) < 5:
        continue
    q = {'number': start + added, 'content': clean(parts[1].strip()),
         'choice1': clean(parts[2]), 'choice2': clean(parts[3]),
         'choice3': clean(parts[4]), 'choice4': clean(parts[5]),
         'choice5': clean(parts[6]), 'answer': ans,
         'explanation': parts[8].strip() if len(parts) > 8 else '',
         'choice_notes': notes}
    qs.append(q)
    added += 1
    print('  + %s번 정답%d  %s' % (q['number'], ans, q['content'][:46]))
    for i in range(1, 6):
        print('      %d) %s' % (i, q['choice%d' % i][:52]))
        print('         %s' % notes[str(i)][:70])
    if added >= need:
        break

json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('\n모두 %d문제' % len(qs))
