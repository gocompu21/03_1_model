"""
NotebookLM 용어 설명을 HTML로 변환하는 스크립트
"""
import json
import re

def markdown_to_html(text):
    """간단한 마크다운을 HTML로 변환"""
    # 헤더 변환
    text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    
    # 굵은 글씨
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    
    # 리스트 변환
    text = re.sub(r'^\* (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    
    # 줄바꿈을 <br>로 변환 (단, 헤더나 리스트 뒤는 제외)
    text = re.sub(r'\n\n', r'</p><p>', text)
    text = f'<p>{text}</p>'
    
    # li 태그 그룹화
    text = re.sub(r'(<li>.*?</li>)(?:\s*<br>)?', r'\1', text)
    
    return text

def generate_html(input_file='notebooklm_explanations.json', output_file='notebooklm_explanations.html'):
    # JSON 로드
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    html_content = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>수목생리학 용어 설명 - NotebookLM</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: 'Noto Sans KR', sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            padding: 40px 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}
        
        header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        
        header h1 {{
            font-size: 2.5rem;
            color: #2d6a4f;
            margin-bottom: 10px;
        }}
        
        header p {{
            color: #666;
            font-size: 1rem;
        }}
        
        .term-card {{
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            overflow: hidden;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}
        
        .term-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 50px rgba(0,0,0,0.15);
        }}
        
        .term-header {{
            background: linear-gradient(135deg, #2d6a4f 0%, #40916c 100%);
            color: white;
            padding: 20px 30px;
        }}
        
        .term-header h2 {{
            font-size: 1.5rem;
            font-weight: 700;
        }}
        
        .term-header .term-id {{
            font-size: 0.85rem;
            opacity: 0.8;
            margin-top: 5px;
        }}
        
        .term-content {{
            padding: 30px;
            line-height: 1.8;
            font-size: 1rem;
            color: #444;
        }}
        
        .term-content h3 {{
            color: #2d6a4f;
            font-size: 1.2rem;
            margin: 25px 0 15px 0;
            padding-left: 15px;
            border-left: 4px solid #40916c;
        }}
        
        .term-content strong {{
            color: #1b4332;
            font-weight: 600;
        }}
        
        .term-content p {{
            margin-bottom: 15px;
        }}
        
        .term-content li {{
            margin-left: 25px;
            margin-bottom: 10px;
            position: relative;
        }}
        
        .term-content li::before {{
            content: "🌿";
            position: absolute;
            left: -25px;
        }}
        
        .source-tag {{
            display: inline-block;
            background: #d8f3dc;
            color: #2d6a4f;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85rem;
            margin-top: 20px;
        }}
        
        footer {{
            text-align: center;
            margin-top: 50px;
            color: #888;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🌳 수목생리학 용어 설명</h1>
            <p>NotebookLM 기반 AI 생성 설명 | 총 {len(data)}개 용어</p>
        </header>
'''

    for item in data:
        word = item.get('word', '')
        term_id = item.get('term_id', '')
        content = item.get('content', '')
        
        # --- 구분자 이후 제거 (소스 태그)
        if '---' in content:
            main_content, source_info = content.split('---', 1)
        else:
            main_content = content
            source_info = ''
        
        # 마크다운을 HTML로 변환
        html_body = markdown_to_html(main_content.strip())
        
        html_content += f'''
        <div class="term-card">
            <div class="term-header">
                <h2>{word}</h2>
                <div class="term-id">ID: {term_id}</div>
            </div>
            <div class="term-content">
                {html_body}
                <span class="source-tag">📚 NotebookLM (수목생리학)</span>
            </div>
        </div>
'''

    html_content += '''
        <footer>
            <p>Generated by NotebookLM-Py | 나무의사 학습 자료</p>
        </footer>
    </div>
</body>
</html>
'''
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ HTML 파일 생성 완료: {output_file}")
    print(f"   총 {len(data)}개 용어 변환됨")

if __name__ == "__main__":
    generate_html()
