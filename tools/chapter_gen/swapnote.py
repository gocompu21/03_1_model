# 선지 설명이 서로 바뀐 것을 맞바꾼다.
#   python swapnote.py <목차id> <문제번호> <선지a> <선지b>
#
# 모델이 설명을 엉뚱한 선지에 붙이는 일이 목차당 한 번꼴로 있다. 칸 수는 5개로
# 맞아서 파서가 못 잡는다. 사람이 읽어야 보이고, 보이면 이걸로 고친다.
import json, sys
sys.stdout.reconfigure(encoding='utf-8')
cid, qno, a, b = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
p = '/tmp/prep/%s.json' % cid
d = json.load(open(p, encoding='utf-8'))
for q in d['questions']:
    if str(q['number']) == qno:
        n = q['choice_notes']
        n[a], n[b] = n[b], n[a]
        print('%s %s번 문제: %s번 <-> %s번 설명 맞바꿈' % (d['code'], qno, a, b))
        for i in range(1, 6):
            print('  %d) %s' % (i, q['choice%d' % i]))
            print('     -> %s' % n[str(i)])
        break
else:
    raise SystemExit('문제 %s 없음' % qno)
json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
