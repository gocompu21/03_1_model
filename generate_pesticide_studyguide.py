"""
농약학 기출문제 기반 수험서 생성기 (HTML 버전)
- 122개 농약 관련 문제를 분석
- 기본서 RAG(수목관리학 스토어)를 통해 해설 생성
- HTML 수험서 출력
"""
import os
import sys
import time
import django
import markdown

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from exam.models import Question
from fileSearchStore import GeminiStoreManager


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>농약학 완벽대비 수험서</title>
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
            line-height: 1.8;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2e7d32;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 15px;
            text-align: center;
        }}
        h2 {{
            color: #388e3c;
            margin-top: 40px;
            border-left: 5px solid #4CAF50;
            padding-left: 15px;
        }}
        h3 {{
            color: #43a047;
            background: #e8f5e9;
            padding: 10px 15px;
            border-radius: 5px;
        }}
        .question-box {{
            background: #fafafa;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            margin: 15px 0;
        }}
        .choices {{
            margin: 15px 0;
        }}
        .choices li {{
            margin: 8px 0;
            padding: 8px;
            background: #fff;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
        }}
        .answer {{
            color: #d32f2f;
            font-weight: bold;
            font-size: 1.1em;
        }}
        .explanation {{
            background: #e3f2fd;
            border-left: 4px solid #2196F3;
            padding: 15px 20px;
            margin: 15px 0;
            border-radius: 0 8px 8px 0;
        }}
        .explanation h4 {{
            color: #1976d2;
            margin-top: 0;
        }}
        .toc {{
            background: #fff3e0;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        .toc h2 {{
            color: #e65100;
            border-left-color: #ff9800;
            margin-top: 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background: #4CAF50;
            color: white;
        }}
        tr:nth-child(even) {{
            background: #f9f9f9;
        }}
        .meta {{
            color: #666;
            text-align: center;
            font-size: 0.9em;
            margin-bottom: 30px;
        }}
        hr {{
            border: none;
            border-top: 1px solid #e0e0e0;
            margin: 30px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        {content}
    </div>
</body>
</html>
"""


def generate_studyguide():
    """농약학 수험서 생성 (HTML)"""
    
    # 기본서 스토어 매니저 초기화
    manager = GeminiStoreManager(api_key=settings.GEMINI_API_KEY)
    store_name = "수목관리학"
    
    # 스토어 확인
    stores = manager.list_stores()
    store_names = [s['name'] for s in stores]
    print(f"사용 가능한 스토어: {store_names}")
    
    if store_name not in store_names:
        print(f"Error: '{store_name}' 스토어를 찾을 수 없습니다.")
        return
    
    # 농약 관련 문제 추출
    keywords = ['농약', '살균제', '살충제', '제초제', '약제', '작용기작', '작용기전']
    all_ids = set()
    for kw in keywords:
        qs = Question.objects.filter(content__icontains=kw)
        for q in qs:
            all_ids.add(q.id)
        qs2 = Question.objects.filter(textbook_chat__icontains=kw)
        for q in qs2:
            all_ids.add(q.id)
    
    questions = Question.objects.filter(id__in=all_ids).select_related('exam').order_by('exam__round_number', 'number')
    total = questions.count()
    print(f"총 {total}개 농약학 관련 문제 발견")
    
    # 주제별 분류
    categories = {
        "살균제": [],
        "살충제": [],
        "제초제": [],
        "작용기작": [],
        "독성학": [],
        "기타": []
    }
    
    for q in questions:
        text = q.content.lower()
        if '살균제' in text or '살균' in text:
            categories["살균제"].append(q)
        elif '살충제' in text or '살충' in text:
            categories["살충제"].append(q)
        elif '제초제' in text or '제초' in text:
            categories["제초제"].append(q)
        elif '작용기작' in text or '작용기전' in text:
            categories["작용기작"].append(q)
        elif 'ld50' in text or '독성' in text or '중독' in text:
            categories["독성학"].append(q)
        else:
            categories["기타"].append(q)
    
    # HTML 콘텐츠 생성
    content = []
    content.append("<h1>🌿 농약학 완벽대비 수험서</h1>")
    content.append(f'<p class="meta">나무의사 기출문제 {total}개 분석 | 생성일: {time.strftime("%Y-%m-%d %H:%M")}</p>')
    
    # 목차
    content.append('<div class="toc">')
    content.append("<h2>📊 목차 및 출제 현황</h2>")
    content.append("<table>")
    content.append("<tr><th>주제</th><th>문제 수</th></tr>")
    for cat, qs in categories.items():
        if qs:
            content.append(f"<tr><td>{cat}</td><td>{len(qs)}개</td></tr>")
    content.append("</table>")
    content.append("</div>")
    
    # 각 카테고리별 문제 및 기본서 해설
    processed = 0
    errors = 0
    
    for cat, cat_questions in categories.items():
        if not cat_questions:
            continue
        
        content.append(f"<h2>📌 {cat}</h2>")
        
        for q in cat_questions[:15]:  # 카테고리당 최대 15문제 (API 제한 고려)
            processed += 1
            print(f"[{processed}] {q.exam.round_number}회 {q.number}번 처리 중...")
            
            content.append(f"<h3>{q.exam.round_number}회 {q.number}번</h3>")
            content.append('<div class="question-box">')
            content.append(f"<p><strong>문제:</strong> {q.content}</p>")
            content.append('<ol class="choices">')
            content.append(f"<li>{q.choice1}</li>")
            content.append(f"<li>{q.choice2}</li>")
            content.append(f"<li>{q.choice3}</li>")
            content.append(f"<li>{q.choice4}</li>")
            content.append(f"<li>{q.choice5}</li>")
            content.append("</ol>")
            content.append(f'<p class="answer">정답: {q.answer}번</p>')
            content.append("</div>")
            
            # 기본서 RAG 조회
            query = f"""다음 문제에 대해 기본서를 기반으로 상세한 해설을 작성해주세요.

문제: {q.content}
보기: ① {q.choice1} ② {q.choice2} ③ {q.choice3} ④ {q.choice4} ⑤ {q.choice5}
정답: {q.answer}번

핵심 개념, 오답 분석, 암기 포인트를 포함해주세요."""
            
            try:
                response = manager.query_store(store_name, query)
                # 마크다운을 HTML로 변환
                html_response = markdown.markdown(response, extensions=['tables', 'fenced_code'])
                content.append('<div class="explanation">')
                content.append("<h4>📚 기본서 해설</h4>")
                content.append(html_response)
                content.append("</div>")
            except Exception as e:
                print(f"  Error: {e}")
                errors += 1
                content.append('<div class="explanation">')
                content.append("<h4>📚 기본서 해설</h4>")
                content.append("<p>(조회 실패)</p>")
                content.append("</div>")
            
            content.append("<hr>")
            
            # Rate limiting
            time.sleep(3)
    
    # HTML 파일 저장
    filename = f"농약학_수험서_{time.strftime('%Y%m%d_%H%M')}.html"
    full_html = HTML_TEMPLATE.format(content="\n".join(content))
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(full_html)
    
    print(f"\n{'='*50}")
    print("완료!")
    print(f"  처리: {processed}개")
    print(f"  에러: {errors}개")
    print(f"  저장: {filename}")


if __name__ == "__main__":
    generate_studyguide()
