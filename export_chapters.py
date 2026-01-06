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

def export_chapters():
    books = Book.objects.all()
    
    for book in books:
        chapters = Chapter.objects.filter(book=book).order_by('order', 'code')
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
