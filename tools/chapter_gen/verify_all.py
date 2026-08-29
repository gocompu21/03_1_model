# 7.1.x 전체를 훑어 빠진 곳이 없는지 확인한다.
import os, django, sys, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '/home/ubuntu/myproject/03_1_model')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from practice.models import Chapter, ChapterContent, PracticeQuestion
from exam.models import TopicQuestionSet
from django.test import Client
from django.contrib.auth.models import User
import os.path as P

ok = lambda b: 'OK  ' if b else 'FAIL'
c = Client()
c.force_login(User.objects.get(username='gocompu21'))


def key(ch):
    return [int(x) for x in ch.code.split('.')]


rows = [ch for ch in Chapter.objects.select_related('book').filter(code__startswith='7.1.')
        if ch.book.subject == '수목해충학']
rows.sort(key=key)

bad = []
tot_q = tot_note = tot_set = 0
print('%-4s %-8s %-14s %6s %6s %5s %6s %s'
      % ('', '코드', '이름', '본문', '이미지', '문제', '설명', '문제집'))
print('-' * 74)
for ch in rows:
    cc = ChapterContent.objects.filter(chapter=ch).first()
    qs = list(PracticeQuestion.objects.filter(chapter=ch))
    ts = TopicQuestionSet.objects.filter(chapter=ch).first()
    s = cc.content if cc else ''
    m = re.search(r'src=.([^"\']+)', s)
    imgf = '/home/ubuntu/myproject/03_1_model' + m.group(1) if m else ''
    pos = (s.find('<img') * 100.0 / len(s)) if s and '<img' in s else -1
    notes = sum(len(q.choice_notes or {}) for q in qs)
    good = (cc and len(s) > 3000 and s.count('<img') == 1 and 0 <= pos < 6
            and imgf and P.exists(imgf)
            and len(qs) >= 5 and all(len(q.choice_notes or {}) == 5 for q in qs)
            and len(set(q.content for q in qs)) == len(qs)
            and not [1 for q in qs for v in (q.choice_notes or {}).values() if '$' in v])
    if not good:
        bad.append(ch.code)
    tot_q += len(qs)
    tot_note += notes
    tot_set += (ts.items.count() if ts else 0)
    print('%-4s %-8s %-14s %6d %5.1f%% %5d %6d %s'
          % (ok(good), ch.code, ch.title[:14], len(s), pos, len(qs), notes,
             ('%d문항' % ts.items.count()) if ts else '-'))

print('-' * 74)
print('목차 %d개 / 연습문제 %d개 / 선지설명 %d개 / 문제집 문항 %d개'
      % (len(rows), tot_q, tot_note, tot_set))
print('문제 있는 목차:', bad or '없음')

# 화면이 열리는지
print()
fails = []
for ch in rows:
    for path in ('/practice/chapter/%d/' % ch.id, '/practice/chapter/%d/detail/' % ch.id):
        if c.get(path).status_code != 200:
            fails.append(path)
print('%s 화면 %d곳 모두 200 %s' % (ok(not fails), len(rows) * 2, fails or ''))
