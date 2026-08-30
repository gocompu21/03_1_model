# 목차 본문 맨 위에 DVD 암기(pestid) 사진을 넣는다.
#   python add_dvd_photo.py <목차id>          # 미리보기
#   python add_dvd_photo.py <목차id> --go     # 실제로 넣기
#
# 사진은 media/uploads/content_images/ 로 복사해 쓴다. pestid 원본을 직접
# 참조하면 해충 앱을 다시 임포트할 때 파일명이 바뀌어 그림이 깨진다.
# 이미 같은 사진이 들어 있으면 넣지 않는다.
import os, django, sys, re, shutil, hashlib
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '/home/ubuntu/myproject/03_1_model')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from django.conf import settings
from practice.models import Chapter, ChapterContent
from pestid.models import PestQuestion

cid = int(sys.argv[1])
GO = '--go' in sys.argv

ch = Chapter.objects.select_related('book').get(id=cid)
cc = ChapterContent.objects.filter(chapter=ch).first()
if not cc:
    raise SystemExit('본문이 없습니다: %s %s' % (ch.code, ch.title))

print('%s %s' % (ch.code, ch.title))

# 목차 이름과 같은 pestid 사진을 찾는다
src = None
for q in PestQuestion.objects.all():
    if ch.title.strip() in [n.strip() for n in (q.name or '').split(',')]:
        src = os.path.join(settings.MEDIA_ROOT, q.image.name)
        break
if not src or not os.path.exists(src):
    raise SystemExit('  DVD 사진이 없습니다')
print('  DVD 사진: %s (%.0fKB)' % (os.path.basename(src),
                                   os.path.getsize(src) / 1024))

# 같은 내용이 이미 들어 있는지 파일 내용으로 본다
digest = hashlib.md5(open(src, 'rb').read()).hexdigest()[:8]
name = 'chapter_%d_dvd_%s.jpg' % (cid, digest)
dst_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', 'content_images')
url = '/media/uploads/content_images/%s' % name

if url in cc.content:
    raise SystemExit('  이미 들어 있습니다')

for m in re.finditer(r'<img[^>]*src="([^"]+)"', cc.content):
    p = os.path.join(settings.MEDIA_ROOT, m.group(1).replace('/media/', '', 1))
    if os.path.exists(p) and hashlib.md5(open(p, 'rb').read()).hexdigest()[:8] == digest:
        raise SystemExit('  같은 사진이 이미 있습니다: %s' % m.group(1))

# 다른 목차와 같은 마크업으로 본문 맨 위에 넣는다
block = ('<div style="text-align:center; margin-bottom:20px;">'
         '<img src="%s" style="width:100%%; max-width:800px; '
         'border-radius:8px; box-shadow:0 4px 10px rgba(0,0,0,0.1);"></div>' % url)

m = re.match(r'<div style="font-family:[^>]*>', cc.content)
out = (cc.content[:m.end()] + '\n' + block + cc.content[m.end():]) if m \
    else block + cc.content

print('  넣을 자리: %s' % ('바깥 div 다음' if m else '맨 앞'))
print('  본문 %d자 -> %d자' % (len(cc.content), len(out)))

if not GO:
    print('  (미리보기 — --go 로 저장)')
    raise SystemExit

os.makedirs(dst_dir, exist_ok=True)
shutil.copy2(src, os.path.join(dst_dir, name))
cc.content = out
cc.save()
print('  넣었습니다: %s' % url)
