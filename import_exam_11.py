"""
11회 기출문제 DB 업로드 스크립트
- 정답(answer)은 업로드하지 않음 (기본값 0으로 설정)
"""
import os
import sys
import django

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

import openpyxl
from exam.models import Exam, Subject, Question

# Load Excel file (relative path)
excel_path = os.path.join(SCRIPT_DIR, 'data', '11회_기출문제.xlsx')
wb = openpyxl.load_workbook(excel_path)
ws = wb.active

# Get or create Exam for round 11
exam, created = Exam.objects.get_or_create(round_number=11)
if created:
    print(f"Created new exam: 11회")
else:
    print(f"Found existing exam: 11회")

# Subject mapping
subject_map = {
    "수목병리학": 1,
    "수목해충학": 2,
    "수목생리학": 3,
    "산림토양학": 4,
    "수목관리학": 5,
}

# Read questions from Excel (skip header row)
created_count = 0
updated_count = 0

for row in ws.iter_rows(min_row=2, max_col=9, values_only=True):
    # Handle both 8 and 9 column formats
    if len(row) >= 9:
        number, subject_name, content, c1, c2, c3, c4, c5, answer = row[:9]
    else:
        number, subject_name, content, c1, c2, c3, c4, c5 = row[:8]
        answer = 0
    
    if number is None:
        continue
    
    # Get subject
    subject_code = subject_map.get(subject_name)
    if not subject_code:
        print(f"Warning: Unknown subject '{subject_name}' for question {number}")
        continue
    
    subject = Subject.objects.get(code=subject_code)
    
    # Create or update question (정답은 0으로 설정 - 업로드하지 않음)
    question, q_created = Question.objects.update_or_create(
        exam=exam,
        number=int(number),
        defaults={
            'subject': subject,
            'content': content or '',
            'choice1': c1 or '',
            'choice2': c2 or '',
            'choice3': c3 or '',
            'choice4': c4 or '',
            'choice5': c5 or '',
            'answer': 0,  # 정답 업로드 안함
            'general_chat': '',  # 해설 없음
        }
    )
    
    if q_created:
        created_count += 1
    else:
        updated_count += 1
    
    print(f"{'Created' if q_created else 'Updated'}: {number}번 ({subject_name})")

print(f"\n=== 완료 ===")
print(f"생성: {created_count}개")
print(f"업데이트: {updated_count}개")
print(f"총: {created_count + updated_count}개")
