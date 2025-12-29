"""
수목병리학 기출문제에서 병명과 출제빈도를 분석하는 스크립트
"""
import os
import sys
import django
import re
from collections import Counter

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from exam.models import Question
from bbs.models import Post, PostType
from django.contrib.auth.models import User
import google.generativeai as genai


def analyze_diseases():
    """수목병리학 문제에서 병명 추출 및 빈도 분석"""
    
    if not settings.GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY is not set")
        return
    
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    # 수목병리학 관련 문제 추출
    keywords = ['병', '균', '바이러스', '세균', '곰팡이', '병원균', '감염', '수목병', '병해', '시들음', '역병', '탄저', '그을음']
    all_ids = set()
    for kw in keywords:
        qs = Question.objects.filter(content__icontains=kw)
        for q in qs:
            all_ids.add(q.id)
    
    questions = Question.objects.filter(id__in=all_ids).select_related('exam').order_by('exam__round_number', 'number')
    total = questions.count()
    print(f"총 {total}개 수목병리학 관련 문제 발견")
    
    # 모든 문제 텍스트 수집
    all_text = ""
    for q in questions:
        all_text += f"[{q.exam.round_number}회 {q.number}번] {q.content} {q.choice1} {q.choice2} {q.choice3} {q.choice4} {q.choice5}\n"
    
    # 일반적인 병명 패턴으로 추출
    disease_patterns = [
        r'[\w가-힣]+병',  # ~병
        r'[\w가-힣]+마름병',  # ~마름병
        r'[\w가-힣]+썩음병',  # ~썩음병
        r'[\w가-힣]+시들음병',  # ~시들음병
        r'[\w가-힣]+역병',  # ~역병
        r'[\w가-힣]+탄저병',  # ~탄저병
        r'[\w가-힣]+점무늬병',  # ~점무늬병
        r'[\w가-힣]+녹병',  # ~녹병
        r'[\w가-힣]+흰가루병',  # ~흰가루병
        r'[\w가-힣]+빗자루병',  # ~빗자루병
    ]
    
    disease_counter = Counter()
    
    for q in questions:
        text = f"{q.content} {q.choice1} {q.choice2} {q.choice3} {q.choice4} {q.choice5}"
        
        # 병명 패턴 매칭
        for pattern in disease_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # 불필요한 접두어 제거
                if len(match) > 2 and match not in ['질병', '수목병', '산림병', '식물병', '수병', '기병']:
                    disease_counter[match] += 1
    
    print(f"\n추출된 병명 수: {len(disease_counter)}개")
    
    # Gemini로 병명 분류 및 정리
    print("\nGemini로 병명 분류 중...")
    
    # 상위 50개 병명 추출
    top_diseases = disease_counter.most_common(100)
    disease_list = "\n".join([f"- {name}: {count}회" for name, count in top_diseases])
    
    prompt = f"""다음은 나무의사 시험 기출문제에서 추출한 병명과 출제 빈도입니다.
이 목록을 검토하고, 병원체 유형별로 분류하여 깔끔하게 정리해주세요.

{disease_list}

## 요청:
1. 병원체 유형별로 분류 (진균병, 세균병, 바이러스병, 기타)
2. 각 분류 내에서 출제 빈도 순으로 정렬
3. 출제 빈도 3회 이상인 병은 **굵게** 표시
4. 동일한 병의 다른 표기는 통합
5. 마크다운 테이블 형식으로 출력

## 출력 형식:
### 진균병 (Fungal Diseases)
| 병명 | 출제 횟수 | 병원균 | 비고 |
|------|-----------|--------|------|
| **소나무재선충병** | 15회 | Bursaphelenchus xylophilus | 매개충: 솔수염하늘소 |

### 세균병 (Bacterial Diseases)
...
"""
    
    try:
        response = model.generate_content(prompt)
        result_text = response.text
        print(result_text[:500] + "...")
    except Exception as e:
        print(f"Error: {e}")
        result_text = "분류 실패"
    
    # HTML 콘텐츠 생성
    import markdown
    
    html_content = f"""
<style>
    .disease-analysis table {{
        border-collapse: collapse;
        width: 100%;
        margin: 15px 0;
    }}
    .disease-analysis th, .disease-analysis td {{
        border: 1px solid #ddd;
        padding: 10px;
        text-align: left;
    }}
    .disease-analysis th {{
        background-color: #4CAF50;
        color: white;
    }}
    .disease-analysis tr:nth-child(even) {{
        background-color: #f9f9f9;
    }}
    .disease-analysis h1 {{
        color: #2e7d32;
        border-bottom: 2px solid #4CAF50;
        padding-bottom: 10px;
    }}
    .disease-analysis h2 {{
        color: #388e3c;
        margin-top: 25px;
    }}
    .disease-analysis h3 {{
        color: #43a047;
    }}
    .disease-analysis strong {{
        color: #1b5e20;
    }}
    .disease-analysis .summary {{
        background: #e8f5e9;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
    }}
</style>
<div class="disease-analysis">
    <h1>🌲 수목병리학 기출문제 - 병명별 출제빈도 분석</h1>
    <div class="summary">
        <p><strong>분석 대상:</strong> {total}개 문제 (5회~11회)</p>
        <p><strong>추출된 병명 수:</strong> {len(disease_counter)}개</p>
        <p><strong>생성일:</strong> {__import__('time').strftime('%Y-%m-%d %H:%M')}</p>
    </div>
    
    <h2>📊 출제 빈도 TOP 20</h2>
    <table>
        <tr><th>순위</th><th>병명</th><th>출제 횟수</th></tr>
"""
    
    for i, (name, count) in enumerate(disease_counter.most_common(20), 1):
        html_content += f"        <tr><td>{i}</td><td><strong>{name}</strong></td><td>{count}회</td></tr>\n"
    
    html_content += """    </table>
    
    <h2>📋 병원체 유형별 분류</h2>
"""
    
    # 마크다운을 HTML로 변환하여 추가
    html_result = markdown.markdown(result_text, extensions=['tables', 'fenced_code'])
    html_content += html_result
    
    html_content += """
</div>
"""
    
    # 게시판에 올리기
    print("\n게시판에 올리는 중...")
    
    admin_user = User.objects.filter(is_staff=True).first()
    if not admin_user:
        admin_user = User.objects.first()
    
    post_type = PostType.objects.filter(name="기본서").first()
    
    post = Post.objects.create(
        type=post_type,
        title="📊 수목병리학 기출문제 - 병명별 출제빈도 분석",
        content=html_content,
        author=admin_user
    )
    
    print(f"\n{'='*50}")
    print("완료!")
    print(f"  분석된 문제: {total}개")
    print(f"  추출된 병명: {len(disease_counter)}개")
    print(f"  게시글 ID: {post.id}")
    print(f"  작성자: {post.author.username}")


if __name__ == "__main__":
    analyze_diseases()
