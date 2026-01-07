"""
Export practice question explanations to JSON (by chapter code + question number).
Usage: python export_explanations.py [--chapter=2.3]
"""
import os
import json
import argparse
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import Chapter, PracticeQuestion

def export_explanations(chapter_prefix=None):
    # Get chapters
    if chapter_prefix:
        chapters = Chapter.objects.filter(code__startswith=chapter_prefix, book_id=1)
        print(f"Exporting questions under chapter '{chapter_prefix}'...")
    else:
        chapters = Chapter.objects.filter(book_id=1)
        print("Exporting all questions...")
    
    questions = PracticeQuestion.objects.filter(chapter__in=chapters).order_by('chapter__code', 'number')
    print(f"Found {questions.count()} questions")
    
    data = []
    for q in questions:
        if q.explanation and len(q.explanation.strip()) > 0:
            data.append({
                "chapter_code": q.chapter.code,
                "number": q.number,
                "explanation": q.explanation
            })
    
    filename = f"explanations_{chapter_prefix.replace('.', '_') if chapter_prefix else 'all'}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Exported {len(data)} explanations to {filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--chapter', type=str, default=None, help='Chapter prefix to filter (e.g., 2.3)')
    args = parser.parse_args()
    export_explanations(args.chapter)
