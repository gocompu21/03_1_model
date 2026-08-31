# 본문 맨 위에 손으로 넣어 둔 DVD 사진(PNG 사본)을 add_dvd_photo.py 와 같은 방식의
# JPEG 사본으로 바꾼다. 7.1.8 ~ 7.1.18 처럼 대시보드에서 올린 PNG 가 pestid 사진과
# 같은 내용인데 파일만 큰(1~2MB) 경우에 쓴다.
#   python swap_dvd_photo.py 490 491 ...        # 미리보기
#   python swap_dvd_photo.py 490 491 ... --go   # 바꾸고, 안 쓰는 옛 파일은 지운다
#
# 바꾸는 조건: 인포그래픽 앞의 첫 <img> 가 pestid 사진과 가로·세로 크기가 같을 때만.
# 크기가 다르면 다른 사진(교과서 그림 등)일 수 있으므로 건드리지 않고 알린다.
import os, django, sys, re, shutil, hashlib
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '/home/ubuntu/myproject/03_1_model')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from django.conf import settings
from PIL import Image
from practice.models import Chapter, ChapterContent
from pestid.models import PestQuestion

GO = '--go' in sys.argv
ids = [int(a) for a in sys.argv[1:] if a.isdigit()]

names = {}
for q in PestQuestion.objects.all():
    for n in (q.name or '').split(','):
        names.setdefault(n.strip(), q)

def media_path(url):
    return os.path.join(settings.MEDIA_ROOT, url.replace('/media/', '', 1))

def referenced(url):
    return ChapterContent.objects.filter(content__contains=url).exists()

for cid in ids:
    ch = Chapter.objects.select_related('book').get(id=cid)
    cc = ChapterContent.objects.filter(chapter=ch).first()
    print('%s %s' % (ch.code, ch.title))
    if not cc:
        print('  본문이 없습니다'); continue
    q = names.get(ch.title.strip())
    if not q:
        print('  DVD 사진이 없습니다'); continue
    src = media_path('/media/' + q.image.name)
    if not os.path.exists(src):
        print('  DVD 사진 파일이 없습니다: %s' % src); continue

    m = re.search(r'<img[^>]*src="([^"]+)"', cc.content)
    if not m or 'temp_infographics' in m.group(1):
        print('  맨 위에 사진이 없습니다 — add_dvd_photo.py 를 쓸 것'); continue
    old = m.group(1)
    old_path = media_path(old)
    if not os.path.exists(old_path):
        print('  옛 파일이 없습니다: %s' % old); continue

    digest = hashlib.md5(open(src, 'rb').read()).hexdigest()[:8]
    if hashlib.md5(open(old_path, 'rb').read()).hexdigest()[:8] == digest:
        print('  이미 같은 파일입니다: %s' % os.path.basename(old)); continue

    a, b = Image.open(src).size, Image.open(old_path).size
    if a != b:
        print('  크기가 다릅니다 (pestid %s, 본문 %s) — 건드리지 않음' % (a, b)); continue

    name = 'chapter_%d_dvd_%s.jpg' % (cid, digest)
    url = '/media/uploads/content_images/%s' % name
    print('  %s (%dKB) -> %s (%dKB)' % (os.path.basename(old), os.path.getsize(old_path) // 1024,
                                        name, os.path.getsize(src) // 1024))
    if not GO:
        continue
    dst_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', 'content_images')
    os.makedirs(dst_dir, exist_ok=True)
    shutil.copy2(src, os.path.join(dst_dir, name))
    cc.content = cc.content.replace(old, url)
    cc.save()
    if not referenced(old):
        os.remove(old_path)
        print('  바꿨고 옛 파일을 지웠습니다')
    else:
        print('  바꿨습니다 (옛 파일은 다른 본문이 써서 남김)')

if not GO:
    print('(미리보기 — --go 로 저장)')
