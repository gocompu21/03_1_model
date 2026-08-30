# 이미 저장된 목차의 이미지를 다시 만들어 본문 속 그림을 갈아 끼운다.
#   python refix_img.py <목차id> "덧붙일 지시"            # 만들고 바로 바꾸기
#   python refix_img.py <목차id> "덧붙일 지시" --no-apply # 파일만 만들기 (본문 안 바꿈)
#   python refix_img.py <목차id> --set <파일명>            # 고른 판으로 바꾸기
#   python refix_img.py <목차id> --show                   # 지금 붙은 그림만 보기
#
# redo_img.py 는 아직 저장 전인 /tmp/prep/<id>.json 을 다룬다. 이미 apply 로
# 저장한 뒤에 잘못을 찾으면 이걸 쓴다. 본문 HTML 의 <img src> 만 바꾸므로
# 문제·문제집은 건드리지 않는다.
#
# 여러 판을 만들어 비교할 때는 --no-apply 로 판을 쌓고, 다 본 뒤 --set 으로
# 한 번만 바꾼다. 그래야 비교하는 동안 사이트에 중간 판이 노출되지 않는다.
import os, django, sys, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '/home/ubuntu/myproject/03_1_model')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from practice.models import Chapter, ChapterContent

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import photoref

args = sys.argv[1:]
cid = int(args[0])
NO_APPLY = '--no-apply' in args
SET = args[args.index('--set') + 1] if '--set' in args else None
SHOW = '--show' in args
extra = next((a for a in args[1:] if not a.startswith('--') and a != SET), '')

ch = Chapter.objects.select_related('book').get(id=cid)
cc = ChapterContent.objects.filter(chapter=ch).first()
if not cc:
    raise SystemExit('본문이 없습니다: %s %s' % (ch.code, ch.title))

cur = re.search(r'(/media/temp_infographics/\S+?\.jpg)', cc.content)
print('%s %s' % (ch.code, ch.title))
print('  지금: %s' % (cur.group(1).split('/')[-1] if cur else '(그림 없음)'))
if SHOW:
    raise SystemExit

if SET:
    if not cur:
        raise SystemExit('본문에 <img> 가 없어 갈아 끼우지 못했습니다.')
    new = '/media/temp_infographics/' + os.path.basename(SET)
    cc.content = cc.content.replace(cur.group(1), new)
    cc.save()
    print('  바꿈: %s' % new.split('/')[-1])
    raise SystemExit

# 본문에서 이미지 태그를 뺀 글만 넘긴다 (prep 때와 같은 방식)
text = re.sub(r'<[^>]+>', ' ', cc.content)
text = re.sub(r'\s+', ' ', text).strip()[:1000]

img, used_photo = photoref.generate(ch, text, extra=extra)
print('  새로: %s%s' % (img.split('/')[-1],
                        ' (사진 참조)' if used_photo else ' (사진 없음)'))

if NO_APPLY:
    print('  (본문은 그대로 — --set 으로 고른 뒤 바꿀 것)')
    raise SystemExit

if not cur:
    raise SystemExit('본문에 <img> 가 없어 갈아 끼우지 못했습니다. 확인이 필요합니다.')

cc.content = cc.content.replace(cur.group(1), img)
cc.save()
print('  본문 교체 완료')
