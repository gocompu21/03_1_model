import os
import django
import sys

sys.path.append('c:/Users/gocom/Documents/Antigravity/Django_BaseCamp/03_1_model')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import Chapter, Book

try:
    # "수목해충학" corresponds to book name likely. Or subject.
    # User said "수목해충학 기본서".
    
    chapters = Chapter.objects.filter(code='1.3.3.8')
    
    print(f"Found {chapters.count()} chapters with code 1.3.3.8:")
    for ch in chapters:
        print(f"ID: {ch.id}, Book: {ch.book.name} ({ch.book.subject}), Title: {ch.title}")

    # Specific search
    target = chapters.filter(book__name__contains='수목해충학').first()
    if not target:
        target = chapters.filter(book__subject__contains='수목해충학').first()
        
    if target:
        print(f"\nTarget Match: ID={target.id}, {target.book.name} - {target.title}")
    else:
        print("\nNo specific match for 수목해충학 found.")
        
except Exception as e:
    print(e)
