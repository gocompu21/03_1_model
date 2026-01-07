"""
Generate PDF for Chapter 2.3 with content and practice questions.
Uses xhtml2pdf to convert styled HTML to PDF.
Usage: python generate_chapter_pdf.py --chapter=2.3
"""
import os
import argparse
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from xhtml2pdf import pisa


from xhtml2pdf import pisa
from practice.models import Chapter, ChapterContent, PracticeQuestion

def natural_sort_key(code):
    """Natural sort for codes like 1.2.3"""
    if not code:
        return (999,)
    parts = code.split('.')
    result = []
    for p in parts:
        try:
            result.append(int(p))
        except ValueError:
            result.append(999)
    return tuple(result)

def generate_pdf(chapter_prefix):
    # Get chapters
    chapters = list(Chapter.objects.filter(code__startswith=chapter_prefix, book_id=1))
    chapters.sort(key=lambda c: natural_sort_key(c.code))
    
    if not chapters:
        print(f"No chapters found for prefix '{chapter_prefix}'")
        return
    
    print(f"Found {len(chapters)} chapters")
    
    # Build HTML content
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {
            size: A4;
            margin: 1.5cm;
        }
        body {
            font-family: 'Malgun Gothic', sans-serif;
            font-size: 10pt;
            line-height: 1.5;
            color: #333;
        }
        h1 { font-size: 20pt; color: #1a5f2a; margin-top: 20px; }
        h2 { font-size: 14pt; color: #2d6a4f; margin-top: 15px; border-bottom: 1px solid #2d6a4f; }
        h3 { font-size: 12pt; color: #40916c; margin-top: 12px; }
        h4 { font-size: 11pt; color: #52b788; margin-top: 10px; }
        .chapter-content { margin: 10px 0; padding: 10px; background: #f8f9fa; }
        .question { margin: 15px 0; padding: 10px; border: 1px solid #dee2e6; }
        .question-header { font-weight: bold; color: #1a5f2a; margin-bottom: 8px; }
        .choices { margin-left: 15px; }
        .choice { margin: 3px 0; }
        .answer { margin-top: 10px; padding: 8px; background: #d8f3dc; }
        .answer-label { font-weight: bold; color: #1a5f2a; }
        .explanation { margin-top: 8px; padding: 8px; background: #e9ecef; }
        .explanation-label { font-weight: bold; color: #495057; }
    </style>
</head>
<body>
"""
    
    # Title
    main_chapter = chapters[0] if chapters else None
    title = f"{chapter_prefix} {main_chapter.title}" if main_chapter else f"Chapter {chapter_prefix}"
    html_content += f"<h1>{title}</h1>\n"
    
    # Chapters with content and questions
    for ch in chapters:
        level = ch.level if hasattr(ch, 'level') else 1
        tag = f"h{min(level+1, 4)}"
        html_content += f"<{tag}>{ch.code} {ch.title}</{tag}>\n"
        
        # Chapter content
        try:
            content = ch.content
            if content and content.content:
                html_content += f"<div class='chapter-content'>{content.content}</div>\n"
        except ChapterContent.DoesNotExist:
            pass
        
        # Practice questions
        questions = PracticeQuestion.objects.filter(chapter=ch).order_by('number')
        if questions.exists():
            for q in questions:
                html_content += "<div class='question'>\n"
                html_content += f"<div class='question-header'>문제 {q.number}</div>\n"
                html_content += f"<div>{q.content}</div>\n"
                
                # Choices
                html_content += "<div class='choices'>\n"
                choices = [q.choice1, q.choice2, q.choice3, q.choice4, q.choice5]
                for i, choice in enumerate(choices, 1):
                    if choice:
                        circled = ["①", "②", "③", "④", "⑤"][i-1]
                        html_content += f"<div class='choice'>{circled} {choice}</div>\n"
                html_content += "</div>\n"
                
                # Answer
                answer = q.answer[0] if isinstance(q.answer, list) else q.answer
                html_content += f"<div class='answer'><span class='answer-label'>정답:</span> {answer}번</div>\n"
                
                # Explanation
                if q.explanation:
                    exp_text = q.explanation.replace('\n', '<br>')
                    html_content += f"<div class='explanation'><span class='explanation-label'>해설:</span><br>{exp_text}</div>\n"
                
                html_content += "</div>\n"
    
    html_content += "</body></html>"
    
    # Save HTML
    html_filename = f"chapter_{chapter_prefix.replace('.', '_')}.html"
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Saved HTML: {html_filename}")
    
    # Generate PDF using xhtml2pdf
    pdf_filename = f"chapter_{chapter_prefix.replace('.', '_')}.pdf"
    with open(pdf_filename, "wb") as pdf_file:
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_file, encoding='utf-8')
    
    if pisa_status.err:
        print(f"Error generating PDF: {pisa_status.err}")
    else:
        print(f"Generated PDF: {pdf_filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--chapter', type=str, default='2.3', help='Chapter prefix (e.g., 2.3)')
    args = parser.parse_args()
    generate_pdf(args.chapter)

