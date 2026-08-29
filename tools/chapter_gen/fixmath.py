# prep 파일에 남은 수식 표기를 글자로 푼다. 잘린 설명도 손본다.
#   $95 \text{cm}^2$ -> 95cm2,  $30 \sim 40 \text{mm}$ -> 30~40mm
import json, re, sys
sys.stdout.reconfigure(encoding='utf-8')

cids = [int(x) for x in sys.argv[1:] if x.isdigit()]


def unmath(t):
    def inner(m):
        s = m.group(1)
        s = re.sub(r'\\text(?:it)?\{([^{}]*)\}', lambda x: x.group(1), s)
        s = re.sub(r'\\sim', '~', s)
        s = re.sub(r'\^\s*\{?\s*2\s*\}?', '²', s)
        s = re.sub(r'\^\s*\{?\s*\\circ\s*\}?', '°', s)
        # 학명은 낱말 사이를 \  로 띄운다 ($Pineus\ orientalis$). 이건 살려야 한다
        if re.search(r'\\ ', s):
            return re.sub(r'\\ ', ' ', s).strip()
        s = re.sub(r'\s+', '', s)
        return s
    t = re.sub(r'\$([^$]*)\$', inner, t)
    return re.sub(r'\s{2,}', ' ', t).strip()


for cid in cids:
    p = '/tmp/prep/%d.json' % cid
    d = json.load(open(p, encoding='utf-8'))
    n = 0
    for q in d['questions']:
        # 문제 본문에도 수식이 섞여 온다 (학명이 특히 그렇다)
        for k in ('content', 'explanation'):
            if q.get(k):
                v = unmath(q[k])
                if v != q[k]:
                    q[k] = v
                    n += 1
        for i in range(1, 6):
            k = 'choice%d' % i
            v = unmath(q[k])
            if v != q[k]:
                q[k] = v
                n += 1
        for k, v in list(q['choice_notes'].items()):
            nv = unmath(v)
            if nv != v:
                q['choice_notes'][k] = nv
                n += 1
    json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    left = ([(q['number'], k) for q in d['questions']
             for k in ('content', 'explanation') if '$' in (q.get(k) or '')] +
            [(q['number'], 'choice%d' % i) for q in d['questions']
             for i in range(1, 6) if '$' in q['choice%d' % i]] +
            [(q['number'], k) for q in d['questions']
             for k, v in q['choice_notes'].items() if '$' in v])
    print('%s %s — %d곳 정리, 남은 수식 %s'
          % (d['code'], d['title'], n, left or '없음'))
