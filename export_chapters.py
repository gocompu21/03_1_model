"""
Script to export chapters from the database to JSON files.
Run: python export_chapters.py
"""
import os
import json
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import Book, Chapter


def natural_sort_key(code):
    """Convert code like '1.2.3' to tuple (1, 2, 3) for proper sorting"""
    if not code:
        return (999,)
    parts = code.split('.')
    result = []
    for p in parts:
        try:
            result.append(int(p))
        except ValueError:
            result.append(999)  # Non-numeric parts go last
    return tuple(result)


def export_chapters():
    books = Book.objects.all()
    
    for book in books:
        chapters = list(Chapter.objects.filter(book=book))
        # Sort by code naturally (1.1 < 1.1.1 < 1.2)
        chapters.sort(key=lambda ch: natural_sort_key(ch.code))
        
        chapter_list = []
        for ch in chapters:
            chapter_list.append({
                "code": ch.code,
                "title": ch.title,
                "level": ch.level
            })
        
        filename = f"chapters_book{book.id}_{book.name.replace(' ', '_')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(chapter_list, f, ensure_ascii=False, indent=2)
        
        print(f"Exported {len(chapter_list)} chapters to {filename}")

if __name__ == "__main__":
    export_chapters()

