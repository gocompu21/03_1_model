# prep 로 만들어 둔 목차의 이미지를 다시 만든다 (틀린 글자가 있을 때).
#   python redo_img.py <목차id> "덧붙일 지시"
import os, django, sys, json, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '/home/ubuntu/myproject/03_1_model')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from django.test import Client
from django.contrib.auth.models import User

cid = int(sys.argv[1])
extra = sys.argv[2] if len(sys.argv) > 2 else ''
p = '/tmp/prep/%d.json' % cid
d = json.load(open(p, encoding='utf-8'))

u = User.objects.filter(is_staff=True, is_superuser=True).first()
c = Client()
c.force_login(u)

ctx = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', d['content'])).strip()[:1000]
ctx = (extra + ' ' if extra else '') + ctx

r = c.post('/dashboard/api/textbook/image/',
           data=json.dumps({'chapter_id': cid, 'context': ctx}),
           content_type='application/json')
res = r.json()
if not res.get('success'):
    raise SystemExit(res)

old = d['image']
d['image'] = res['image_url']
json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('%s -> %s' % (old.split('/')[-1], d['image'].split('/')[-1]))
