
import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import Book, Chapter

def check_data():
    books = Book.objects.all()
    print(f"Total Books: {books.count()}")
    for book in books:
        print(f" - Book: {book.subject} | {book.name} (ID: {book.id})")
        chapters = book.chapters.all()
        print(f"   - Chapters: {chapters.count()}")
        if chapters.count() > 0:
            print(f"     First Chapter: {chapters.first().title}")

if __name__ == '__main__':
    check_data()
