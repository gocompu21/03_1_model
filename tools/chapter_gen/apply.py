# prep.py 가 만들어 둔 것을 확인 후 실제로 저장한다.
#   본문(이미지 맨 위) -> 문제 -> 주제별 문제집
import os, django, sys, json, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '/home/ubuntu/myproject/03_1_model')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from practice.models import Chapter, ChapterContent, PracticeQuestion
from exam.models import Question, Subject, TopicQuestionSet

CHS = [int(x) for x in sys.argv[1:] if x.isdigit()]
DRY = '--go' not in sys.argv
assert CHS, '목차 id 를 넘겨 주세요'

u = User.objects.filter(is_staff=True, is_superuser=True).first()
c = Client()
c.force_login(u)
SUB = Subject.objects.get(id=2)


def post(url, payload):
    r = c.post(url, data=json.dumps(payload), content_type='application/json')
    d = r.json()
    if not d.get('success'):
        raise RuntimeError('%s -> %s' % (url, d.get('error')))
    return d


for cid in CHS:
    d = json.load(open('/tmp/prep/%d.json' % cid, encoding='utf-8'))
    ch = Chapter.objects.get(id=cid)
    print('\n=== %s %s' % (d['code'], d['title']))

    # 이미지를 맨 위에 넣는다 (다른 목차와 같은 마크업)
    html, img = d['content'], d['image']
    block = ('<div style="text-align:center; margin-bottom:20px;">'
             '<img src="%s" style="width:100%%; max-width:800px; '
             'border-radius:8px; box-shadow:0 4px 10px rgba(0,0,0,0.1);"></div>' % img)
    m = re.match(r'<div style="font-family:[^>]*>', html)
    out = html[:m.end()] + '\n' + block + html[m.end():] if m else block + html

    good = [q for q in d['questions'] if len(q.get('choice_notes') or {}) == 5]
    kw = ch.title

    # 이름이 더 긴 종 이름 안에 통째로 들어가면 그 문항까지 딸려 온다.
    # ('선녀벌레' 로 찾으면 '미국선녀벌레' 문항이 잡힌다)
    longer = [c.title for c in Chapter.objects.select_related('book')
              .filter(code__startswith='7.', title__contains=kw)
              if c.id != ch.id and c.book.subject == '수목해충학'
              and c.title != kw]

    def texts(q):
        dd = {'본문': q.content or ''}
        for i in range(1, 6):
            dd['선지%d' % i] = getattr(q, 'choice%d' % i) or ''
        return dd

    def has(q):
        for v in texts(q).values():
            t = v
            for e in longer:      # 더 긴 이름을 지운 뒤에 찾는다
                t = t.replace(e, '')
            if kw in t:
                return True
        return False

    hits = [q for q in Question.objects.filter(subject=SUB).select_related('exam')
            .order_by('exam__round_number', 'number') if has(q)]

    print('  본문 %d자 (이미지 %.1f%%)  문제 %d개  기출 %d문항'
          % (len(out), out.find('<img') * 100.0 / len(out), len(good), len(hits)))

    if DRY:
        print('  (미리보기 — --go 로 저장)')
        continue

    post('/dashboard/api/textbook/save-content/', {'chapter_id': cid, 'content': out})
    if good:
        n = post('/dashboard/api/textbook/save-quiz/',
                 {'chapter_id': cid, 'questions': good})['created_count']
        print('  문제 %d개 저장' % n)
    if hits and not TopicQuestionSet.objects.filter(subject=SUB, chapter=ch).exists():
        r = post('/study/api/save_topic_set/', {
            'title': '%s %s' % (d['code'], d['title']), 'description': '',
            'subject_id': SUB.id, 'chapter_id': cid,
            'question_ids': [q.id for q in hits]})
        print('  문제집 id=%s (%s)' % (r['topic_set_id'],
              ', '.join('%d-%d' % (q.exam.round_number, q.number) for q in hits)))
    elif not hits:
        print('  기출 0문항 — 문제집 없음')
    print('  저장 완료')
