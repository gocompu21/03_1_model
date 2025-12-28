"""
농약 분석 결과를 게시판에 올리는 스크립트
마크다운을 HTML로 변환하여 포맷이 적용되도록 함
"""
import os
import sys
import django
import markdown

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from bbs.models import Post, PostType
from django.contrib.auth.models import User


def post_pesticide_analysis():
    """농약 분석 결과를 게시판에 포스팅"""
    
    # 마크다운 파일 읽기
    with open("pesticide_analysis_with_frequency.md", "r", encoding="utf-8") as f:
        md_content = f.read()
    
    # 마크다운을 HTML로 변환
    html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
    
    # 스타일 추가
    styled_content = f"""
<style>
    .pesticide-analysis table {{
        border-collapse: collapse;
        width: 100%;
        margin: 15px 0;
    }}
    .pesticide-analysis th, .pesticide-analysis td {{
        border: 1px solid #ddd;
        padding: 8px;
        text-align: left;
    }}
    .pesticide-analysis th {{
        background-color: #4CAF50;
        color: white;
    }}
    .pesticide-analysis tr:nth-child(even) {{
        background-color: #f9f9f9;
    }}
    .pesticide-analysis h1 {{
        color: #2e7d32;
        border-bottom: 2px solid #4CAF50;
        padding-bottom: 10px;
    }}
    .pesticide-analysis h2 {{
        color: #388e3c;
        margin-top: 25px;
    }}
    .pesticide-analysis h3 {{
        color: #43a047;
    }}
    .pesticide-analysis strong {{
        color: #1b5e20;
    }}
</style>
<div class="pesticide-analysis">
{html_content}
</div>
"""
    
    # 관리자 계정 찾기
    admin_user = User.objects.filter(is_staff=True).first()
    if not admin_user:
        admin_user = User.objects.first()
    
    # 게시글 유형 (일반 질의 또는 기본서)
    post_type = PostType.objects.filter(name="기본서").first()
    
    # 게시글 생성
    post = Post.objects.create(
        type=post_type,
        title="📊 나무의사 기출문제 - 작용기작별 농약 정리 (출제 빈도 포함)",
        content=styled_content,
        author=admin_user
    )
    
    print(f"게시글 작성 완료!")
    print(f"  제목: {post.title}")
    print(f"  작성자: {post.author.username}")
    print(f"  게시글 ID: {post.id}")


if __name__ == "__main__":
    post_pesticide_analysis()
