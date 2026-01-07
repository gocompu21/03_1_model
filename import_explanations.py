"""
Import practice question explanations from JSON (by chapter code + question number).
Usage: python import_explanations.py --file=explanations_2_3.json [--dry-run]
"""
import os
import json
import argparse
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import Chapter, PracticeQuestion

def import_explanations(filename, dry_run=False):
    if not os.path.exists(filename):
        print(f"ERROR: File not found: {filename}")
        return
    
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Found {len(data)} explanations in file")
    if dry_run:
        print("DRY RUN MODE - No changes will be made")
    
    updated = 0
    skipped = 0
    not_found = 0
    
    for item in data:
        chapter_code = item.get("chapter_code", "")
        number = item.get("number", 0)
        explanation = item.get("explanation", "")
        
        if not chapter_code or not number or not explanation:
            skipped += 1
            continue
        
        # Find question by chapter code and number
        try:
            chapter = Chapter.objects.get(code=chapter_code, book_id=1)
            question = PracticeQuestion.objects.get(chapter=chapter, number=number)
            
            if dry_run:
                print(f"[DRY RUN] Would update: {chapter_code} #{number}")
            else:
                question.explanation = explanation
                question.save()
            updated += 1
            
        except Chapter.DoesNotExist:
            print(f"Chapter not found: {chapter_code}")
            not_found += 1
        except PracticeQuestion.DoesNotExist:
            print(f"Question not found: {chapter_code} #{number}")
            not_found += 1
    
    print(f"\n--- Summary ---")
    print(f"Updated: {updated}")
    print(f"Skipped: {skipped}")
    print(f"Not found: {not_found}")
    if dry_run:
        print("(DRY RUN - No actual changes made)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, required=True, help='JSON file to import')
    parser.add_argument('--dry-run', action='store_true', help='Preview without saving')
    args = parser.parse_args()
    import_explanations(args.file, args.dry_run)
