"""
농약학 핵심 정리 내용을 게시판에 올리는 스크립트
"""
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from bbs.models import Post, PostType
from django.contrib.auth.models import User

html_content = '''
<style>
    .study-guide { font-family: 'Malgun Gothic', sans-serif; line-height: 1.8; }
    .study-guide h1 { color: #1a5f2e; border-bottom: 3px solid #2e7d32; padding-bottom: 10px; }
    .study-guide h2 { color: #2e7d32; margin-top: 30px; border-left: 4px solid #4CAF50; padding-left: 10px; background: #e8f5e9; padding: 10px; }
    .study-guide h3 { color: #388e3c; }
    .study-guide .section { background: #f9f9f9; border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin: 15px 0; }
    .study-guide .exam-questions { background: #e3f2fd; border-left: 4px solid #2196F3; padding: 15px; margin: 10px 0; }
    .study-guide .expected { background: #fff3e0; border-left: 4px solid #ff9800; padding: 15px; margin: 10px 0; }
    .study-guide .tip { background: #fce4ec; border-left: 4px solid #e91e63; padding: 15px; margin: 20px 0; border-radius: 0 8px 8px 0; }
    .study-guide strong { color: #1b5e20; }
    .study-guide table { border-collapse: collapse; width: 100%; margin: 15px 0; }
    .study-guide th, .study-guide td { border: 1px solid #ddd; padding: 10px; text-align: left; }
    .study-guide th { background: #4CAF50; color: white; }
</style>
<div class="study-guide">
<h1>📚 수목관리학 - 농약학 핵심 정리</h1>

<h2>Chapter 1. 농약의 정의 및 관련 법규</h2>
<div class="section">
<p>수목 진료 시 사용하는 약제의 법적 범주와 등록 절차를 이해해야 합니다.</p>
<h3>주요 내용:</h3>
<ul>
    <li><strong>농약의 범주:</strong> 살균제, 살충제, 제초제 외에 식물생장조절제, 전착제, 유인제, 천적, 미생물제제가 포함됩니다. (※ 주의: 제초제 저항성 GMO 작물은 농약이 아님)</li>
    <li><strong>등록 및 취소:</strong> 농약의 품목 등록권자는 <strong>농촌진흥청장</strong>입니다. 주요 취소 사유는 맹독성(파라쿼트), 난분해성(DDT), 생물농축(수은제) 등입니다.</li>
</ul>
</div>
<div class="exam-questions">
<h3>📝 기출문제 (수목관리학 5~11회):</h3>
<ul>
    <li>[5회 126번, 6회 123번] 농약관리법상 농약의 범주에 속하지 않는 것은?</li>
    <li>[5회 130번] 한국의 농약 품목 등록권자는?</li>
    <li>[6회 124번] 등록 취소 농약의 사유가 옳지 않은 것은?</li>
</ul>
</div>
<div class="expected">
<h3>💡 예상문제:</h3>
<p><strong>Q.</strong> 농약관리법상 천적이 농약의 범주에 포함되는 근거는 무엇인가?</p>
<p><strong>A.</strong> 농약관리법 시행령 제2조에 따라 병해충 방제에 이용되는 생물인 천적은 농약에 해당함.</p>
</div>

<h2>Chapter 2. 살충제의 작용기작 및 약제 특성</h2>
<div class="section">
<p>작용기작 분류 기호(IRAC)와 대상 해충의 연결이 핵심입니다.</p>
<h3>주요 내용:</h3>
<table>
    <tr><th>그룹</th><th>작용기작</th><th>대표 약제</th><th>대상 해충</th></tr>
    <tr><td>1b</td><td>AChE 저해 (유기인계)</td><td>페니트로티온</td><td>-</td></tr>
    <tr><td>1a</td><td>AChE 저해 (카바메이트계)</td><td>카보퓨란</td><td>-</td></tr>
    <tr><td>4a</td><td>nAChR 경쟁적 변조</td><td><strong>아세타미프리드, 이미다클로프리드</strong></td><td>진딧물, 깍지벌레, 솔잎혹파리</td></tr>
    <tr><td>6</td><td>Cl⁻ 통로 활성화</td><td><strong>아바멕틴, 에마멕틴벤조에이트</strong></td><td>재선충병 예방, 응애류</td></tr>
    <tr><td>15</td><td>키틴합성저해 (IGR)</td><td><strong>디플루벤주론(디밀린)</strong></td><td>유충 탈피 방해</td></tr>
    <tr><td>-</td><td>미생물 살충제</td><td>Bt(바실러스 튜린기엔시스)</td><td>나비목 유충 중장 파괴</td></tr>
</table>
</div>
<div class="exam-questions">
<h3>📝 기출문제:</h3>
<ul>
    <li>[5회 129번, 7회 123번] 키틴 합성을 저해하여 탈피를 방해하는 살충제는?</li>
    <li>[8회 121번] 신경 및 근육 자극 전달 저해제가 아닌 것은? (정답: 디플루벤주론)</li>
    <li>[11회 116번] 아세타미프리드에 관한 설명으로 옳지 않은 것은? (정답: 꿀벌에 독성이 높음)</li>
</ul>
</div>

<h2>Chapter 3. 살균제의 분류 및 수목병 방제</h2>
<div class="section">
<p><strong>보호살균제</strong>(예방)와 <strong>침투이행성 살균제</strong>(치료)를 구분해야 합니다.</p>
<h3>주요 내용:</h3>
<ul>
    <li><strong>보호살균제:</strong> 만코제브, 석회보르도액, 동제. 식물 표면에 부착되어 포자 발아를 차단</li>
    <li><strong>침투성 살균제 (트리아졸계):</strong> <strong>테부코나졸</strong>, 마이클로뷰타닐. 에르고스테롤 생합성 저해. 수간주사 및 상처도포제로 사용</li>
    <li><strong>항생제:</strong> <strong>옥시테트라사이클린</strong>(파이토플라스마-빗자루병), 바리다마이신(잔디 라이조토니아병)</li>
</ul>
</div>
<div class="exam-questions">
<h3>📝 기출문제:</h3>
<ul>
    <li>[6회 132번, 8회 122번] 테부코나졸의 작용기작은? (정답: 스테롤 합성 저해)</li>
    <li>[8회 117번] 보호살균제에 관한 설명으로 옳지 않은 것은?</li>
    <li>[11회 119번] 호흡작용을 저해하는 살균제가 아닌 것은? (정답: 베노밀-세포분열 저해)</li>
</ul>
</div>

<h2>Chapter 4. 제초제의 작용성 및 수목 약해</h2>
<div class="section">
<p>제초제의 선택성과 수목에 미치는 약해 증상이 빈출됩니다.</p>
<h3>주요 내용:</h3>
<ul>
    <li><strong>호르몬계 제초제 (그룹 O):</strong> <strong>2,4-D, 디캄바</strong>. 옥신 유사 작용. 수목에 비산 시 잎 뒤틀림, 가지 이상비대 유발</li>
    <li><strong>아미노산 저해 제초제 (비선택성):</strong> <strong>글리포세이트</strong>(EPSPS 저해, 토양 불활성화), 글루포시네이트(GS 저해)</li>
    <li><strong>선택성:</strong> 플루아지포프-P-뷰틸(벼과 잡초만 제거), 벤타존(대사적 무독화 차이로 선택성 발휘)</li>
</ul>
</div>
<div class="exam-questions">
<h3>📝 기출문제:</h3>
<ul>
    <li>[5회 122번] 제초제 피해 설명 중 틀린 것은? (정답: 2,4-D는 호르몬계임)</li>
    <li>[8회 120번] 벤타존의 선택성 원인은? (정답: 대사에 의한 무독화)</li>
    <li>[11회 114번] 수목의 제초제 약해 증상이 아닌 것은?</li>
</ul>
</div>

<h2>Chapter 5. 농약 제형 및 보조제</h2>
<div class="section">
<p>수간주사용 제형과 항공방제용 제형의 특징이 중요합니다.</p>
<h3>주요 내용:</h3>
<ul>
    <li><strong>수간주사용:</strong> 미탁제(ME), 분산성액제(DC). 입자가 작아 침투이행이 빠름</li>
    <li><strong>액제(SL) vs 유제(EC):</strong> 액제는 투명한 수용액, 유제는 우윳빛 유탁액(유화제 포함)</li>
    <li><strong>특수제형:</strong> 미량살포액제(UL). 항공방제용 고농도 제형</li>
    <li><strong>보조제:</strong> 협력제(약효 상승), 계면활성제(표면장력과 접촉각을 낮춰 전착 효과 증대)</li>
</ul>
</div>
<div class="exam-questions">
<h3>📝 기출문제:</h3>
<ul>
    <li>[6회 126번] 계면활성제의 역할로 옳지 않은 것은? (정답: 접촉각을 크게 함)</li>
    <li>[7회 135번] 항공방제에 사용되는 농축된 특수 제형은?</li>
    <li>[10회 117번] 제제 형태가 액상이 아닌 것은? (정답: 수용제-고체 분말)</li>
</ul>
</div>

<h2>Chapter 6. 계산 및 안전 관리</h2>
<div class="section">
<p>농약 농도 환산 및 수목의 안전 관리 기준입니다.</p>
<h3>주요 내용:</h3>
<ul>
    <li><strong>농도 계산:</strong> 1% = 10,000 ppm</li>
    <li><strong>수간주사량:</strong> 흉고직경(DBH)에 비례하여 약제량 결정</li>
    <li><strong>안전 기준:</strong> NOEL(최대무독성용량) → ADI(1일 섭취허용량) → MRL(잔류허용기준) 설정</li>
    <li><strong>PLS:</strong> 농약 허용물질목록관리제도는 불검출 수준(0.01 mg/kg)으로 관리</li>
</ul>
</div>
<div class="exam-questions">
<h3>📝 기출문제:</h3>
<ul>
    <li>[5회 134번] 아바멕틴 1.8% 원액의 ppm 농도와 수간주사 용기 개수 계산</li>
    <li>[7회 133번] 농약 잔류허용기준(MRL)의 법적 근거는? (정답: 식품위생법)</li>
    <li>[10회 118번] 농약 안전사용기준 설정 과정 모식도 용어 연결</li>
</ul>
</div>

<div class="tip">
<h3>🎓 교수님의 학습 팁:</h3>
<p>수목관리학 내 농약 문제는 <strong>수간주사(아바멕틴, 이미다클로프리드, 테부코나졸)</strong>와 <strong>제초제 약해(디캄바)</strong>에 집중되어 있습니다.</p>
<p>농약학 과목과 겹치는 이론 문제는 <strong>작용기작 분류번호</strong>를 중심으로 공부하되, 계산 문제는 반드시 손으로 직접 풀어 단위를 맞추는 연습을 하십시오.</p>
</div>
</div>
'''

admin_user = User.objects.filter(is_staff=True).first()
post_type = PostType.objects.filter(name="기본서").first()

post = Post.objects.create(
    type=post_type,
    title="📚 수목관리학 - 농약학 핵심 정리 (Chapter 1~6)",
    content=html_content,
    author=admin_user
)

print(f"게시글 작성 완료!")
print(f"  제목: {post.title}")
print(f"  게시글 ID: {post.id}")
print(f"  작성자: {post.author.username}")
