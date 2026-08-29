# 만들어 둔 문제집이 실제로 그 해충의 문항만 담고 있는지 전수 점검한다.
#   - 이름이 다른 종 이름 안에 들어가면 엉뚱한 문항이 딸려 온다
#   - 빈 문제집은 지운다
import os, django, sys, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '/home/ubuntu/myproject/03_1_model')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from exam.models import Question, Subject, TopicQuestionSet, TopicQuestionSetItem
from practice.models import Chapter

DRY = '--go' not in sys.argv
SUB = Subject.objects.get(id=2)

names = {}
for ch in Chapter.objects.select_related('book').filter(code__startswith='7.'):
    if ch.book.subject == '수목해충학':
        names[ch.id] = ch.title


def texts(q):
    d = {'본문': q.content or ''}
    for i in range(1, 6):
        d['선지%d' % i] = getattr(q, 'choice%d' % i) or ''
    return d


allq = list(Question.objects.filter(subject=SUB).select_related('exam')
            .order_by('exam__round_number', 'number'))

bad, empty = [], []
for ts in (TopicQuestionSet.objects.filter(subject=SUB, chapter__isnull=False)
           .select_related('chapter')):
    ch = ts.chapter
    title = ch.title
    # 이 이름을 통째로 품는 더 긴 이름들
    longer = [t for i, t in names.items() if i != ch.id and title in t and title != t]

    want = []
    for q in allq:
        for v in texts(q).values():
            t = v
            for e in longer:
                t = t.replace(e, '')
            if title in t:
                want.append(q)
                break

    have = [i.question_id for i in ts.items.all()]
    if not want:
        empty.append((ch.code, title, ts.id, len(have)))
    elif sorted(have) != sorted(q.id for q in want):
        bad.append((ch.code, title, ts.id, len(have), len(want), want))

print('문제집 %d개 점검' % TopicQuestionSet.objects.filter(subject=SUB, chapter__isnull=False).count())
print()
print('■ 담긴 문항이 실제와 다른 곳: %d개' % len(bad))
for code, title, tsid, h, w, _ in bad:
    print('   %-8s %-14s %d -> %d문항' % (code, title, h, w))
print()
print('■ 기출이 없는데 남아 있는 문제집: %d개' % len(empty))
for code, title, tsid, h in empty:
    print('   %-8s %-14s (%d문항 담김)' % (code, title, h))

if DRY:
    print('\n(--go 로 고침)')
    raise SystemExit

for code, title, tsid, h, w, want in bad:
    ts = TopicQuestionSet.objects.get(id=tsid)
    TopicQuestionSetItem.objects.filter(question_set=ts).delete()
    for i, q in enumerate(want):
        TopicQuestionSetItem.objects.create(question_set=ts, question=q, order=i)
    print('고침 %s %s -> %d문항' % (code, title, w))

for code, title, tsid, h in empty:
    TopicQuestionSet.objects.filter(id=tsid).delete()
    print('삭제 %s %s (기출 없음)' % (code, title))
