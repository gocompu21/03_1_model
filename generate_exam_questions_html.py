"""
Generate HTML for specific exam questions.
Usage: python generate_exam_questions_html.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from exam.models import Exam, Question

# List of questions to include: (round, number)
QUESTIONS = [
    (5, 2),
    (6, 10),
    (8, 7),
    (9, 6),
    (9, 24),
    (10, 1),
    (11, 2),
    (11, 9),
    (11, 10),
    (11, 12),
    (11, 15),
    (11, 16),
    (11, 17),
]

def generate_html():
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>기출학습문제 모음</title>
    <style>
        @page {
            size: A4;
            margin: 1.5cm;
        }
        body {
            font-family: 'Malgun Gothic', sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 { 
            font-size: 18pt; 
            color: #1a5f2a; 
            text-align: center;
            border-bottom: 2px solid #1a5f2a;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }
        .question { 
            margin: 25px 0; 
            padding: 15px; 
            border: 1px solid #dee2e6; 
            border-radius: 8px;
            background: #fff;
            page-break-inside: avoid;
        }
        .question-header { 
            font-weight: bold; 
            color: #1a5f2a; 
            font-size: 13pt;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid #e9ecef;
        }
        .question-content {
            margin-bottom: 15px;
        }
        .choices { 
            margin-left: 10px; 
            margin-bottom: 15px;
        }
        .choice { 
            margin: 6px 0; 
            padding: 5px 0;
        }
        .answer { 
            margin-top: 12px; 
            padding: 10px; 
            background: #d8f3dc; 
            border-radius: 5px;
        }
        .answer-label { 
            font-weight: bold; 
            color: #1a5f2a; 
        }
        .explanation { 
            margin-top: 12px; 
            padding: 12px; 
            background: #f8f9fa; 
            border-left: 4px solid #1a5f2a;
            border-radius: 0 5px 5px 0;
        }
        .explanation-label { 
            font-weight: bold; 
            color: #495057; 
            display: block;
            margin-bottom: 8px;
        }
    </style>
</head>
<body>
<h1>기출학습문제 모음</h1>
"""
    
    not_found = []
    
    for round_num, q_num in QUESTIONS:
        try:
            exam = Exam.objects.get(round_number=round_num)
            question = Question.objects.get(exam=exam, number=q_num)
            
            html_content += f"<div class='question'>\n"
            html_content += f"<div class='question-header'>{round_num}회 {q_num}번</div>\n"
            html_content += f"<div class='question-content'>{question.content}</div>\n"
            
            # Choices
            html_content += "<div class='choices'>\n"
            choices = [question.choice1, question.choice2, question.choice3, question.choice4, question.choice5]
            circled = ["①", "②", "③", "④", "⑤"]
            for i, choice in enumerate(choices):
                if choice:
                    html_content += f"<div class='choice'>{circled[i]} {choice}</div>\n"
            html_content += "</div>\n"
            
            # Answer
            answer = question.answer[0] if isinstance(question.answer, list) and question.answer else question.answer
            html_content += f"<div class='answer'><span class='answer-label'>정답:</span> {answer}번</div>\n"
            
            # Explanation (prefer textbook_chat, fallback to general_chat)
            explanation = question.textbook_chat if question.textbook_chat else question.general_chat
            if explanation:
                exp_text = explanation.replace('\n', '<br>')
                html_content += f"<div class='explanation'><span class='explanation-label'>해설:</span>{exp_text}</div>\n"
            
            html_content += "</div>\n"
            print(f"Added: {round_num}회 {q_num}번")
            
        except Exam.DoesNotExist:
            not_found.append(f"{round_num}회 (Exam not found)")
        except Question.DoesNotExist:
            not_found.append(f"{round_num}회 {q_num}번")
    
    html_content += "</body></html>"
    
    # Save HTML
    filename = "exam_questions_selected.html"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\nSaved: {filename}")
    
    if not_found:
        print(f"\nNot found: {', '.join(not_found)}")

if __name__ == "__main__":
    generate_html()
