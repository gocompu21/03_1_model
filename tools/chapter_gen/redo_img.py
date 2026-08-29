# prep 로 만들어 둔 목차의 이미지를 다시 만든다 (틀린 글자가 있을 때).
#   python redo_img.py <목차id> "덧붙일 지시"
# 지시는 영어로 쓴다. 한글 예시를 넣으면 그 글자가 그림에 그대로 찍힌다.
import os, django, sys, json, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '/home/ubuntu/myproject/03_1_model')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from practice.models import Chapter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import photoref

cid = int(sys.argv[1])
extra = sys.argv[2] if len(sys.argv) > 2 else ''
p = '/tmp/prep/%d.json' % cid
d = json.load(open(p, encoding='utf-8'))

ch = Chapter.objects.select_related('book').get(id=cid)
ctx = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', d['content'])).strip()[:1000]

img, used_photo = photoref.generate(ch, ctx, extra=extra)

old = d['image']
d['image'] = img
json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('%s -> %s%s' % (old.split('/')[-1], img.split('/')[-1],
                      ' (사진 참조)' if used_photo else ' (사진 없음)'))
