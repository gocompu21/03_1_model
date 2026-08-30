# 목차들이 본문에 DVD 사진을 갖고 있는지 훑는다.
#   python audit_dvd_photo.py 7.1.21        # 그 절 번호부터 끝까지
#   python audit_dvd_photo.py 7.1.21 7.2.60 # 구간
#
# 상태: 있음(이미 들어감) / 넣기 / 사진없음(pestid 에 같은 이름이 없음)
import os, django, sys, re, hashlib
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '/home/ubuntu/myproject/03_1_model')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from django.conf import settings
from practice.models import Chapter, ChapterContent
from pestid.models import PestQuestion

start = sys.argv[1] if len(sys.argv) > 1 else '7.1.1'
end = sys.argv[2] if len(sys.argv) > 2 else '7.9.99'


def key(code):
    return [int(x) for x in code.split('.')]


photos = {}
for q in PestQuestion.objects.all():
    for nm in (q.name or '').split(','):
        nm = nm.strip()
        if nm:
            photos.setdefault(nm, q)

rows = []
for ch in Chapter.objects.select_related('book').filter(code__startswith='7.'):
    if ch.book.subject != '수목해충학':
        continue
    try:
        k = key(ch.code)
    except ValueError:
        continue
    if not (key(start) <= k <= key(end)):
        continue
    rows.append((k, ch))
rows.sort()

todo = []
for _, ch in rows:
    cc = ChapterContent.objects.filter(chapter=ch).first()
    if not cc:
        print('%-8s %-20s 본문없음' % (ch.code, ch.title[:20]))
        continue
    q = photos.get(ch.title.strip())
    if not q:
        print('%-8s %-20s 사진없음' % (ch.code, ch.title[:20]))
        continue
    src = os.path.join(settings.MEDIA_ROOT, q.image.name)
    if not os.path.exists(src):
        print('%-8s %-20s 파일없음 %s' % (ch.code, ch.title[:20], q.image.name))
        continue
    digest = hashlib.md5(open(src, 'rb').read()).hexdigest()[:8]

    have = False
    for m in re.finditer(r'<img[^>]*src="([^"]+)"', cc.content):
        p = os.path.join(settings.MEDIA_ROOT, m.group(1).replace('/media/', '', 1))
        if os.path.exists(p) and \
                hashlib.md5(open(p, 'rb').read()).hexdigest()[:8] == digest:
            have = True
            break
    if have:
        print('%-8s %-20s 있음' % (ch.code, ch.title[:20]))
    else:
        print('%-8s %-20s 넣기   (img %d개)' % (ch.code, ch.title[:20],
                                                cc.content.count('<img')))
        todo.append(ch.id)

print('\n넣을 목차 %d개' % len(todo))
print(' '.join(str(i) for i in todo))
