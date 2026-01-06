"""
Django management command to sync chapters from a local JSON file to the database.
Usage: python manage.py sync_chapters --file=chapters.json --book_id=1

JSON File Format:
[
    {"code": "1", "title": "서론", "level": 1},
    {"code": "1.1", "title": "개요", "level": 2},
    {"code": "1.1.1", "title": "정의", "level": 3},
    ...
]
"""
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from practice.models import Book, Chapter


class Command(BaseCommand):
    help = 'Sync chapters from a JSON file to the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='Path to the JSON file containing chapter data',
        )
        parser.add_argument(
            '--book_id',
            type=int,
            required=True,
            help='ID of the book to sync chapters to',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing chapters before syncing (WARNING: destructive)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without actually modifying the database',
        )

    def handle(self, *args, **options):
        file_path = Path(options['file'])
        book_id = options['book_id']
        clear_existing = options['clear']
        dry_run = options['dry_run']

        # Validate file exists
        if not file_path.exists():
            raise CommandError(f'File not found: {file_path}')

        # Validate book exists
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            raise CommandError(f'Book with ID {book_id} not found')

        self.stdout.write(f"Syncing chapters for: {book.subject} - {book.name}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        # Load JSON data
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                chapters_data = json.load(f)
        except json.JSONDecodeError as e:
            raise CommandError(f'Invalid JSON file: {e}')

        if not isinstance(chapters_data, list):
            raise CommandError('JSON file must contain an array of chapter objects')

        self.stdout.write(f"Found {len(chapters_data)} chapters in file")

        # Clear existing chapters if requested
        if clear_existing:
            if dry_run:
                existing_count = Chapter.objects.filter(book=book).count()
                self.stdout.write(f"  [DRY RUN] Would delete {existing_count} existing chapters")
            else:
                deleted, _ = Chapter.objects.filter(book=book).delete()
                self.stdout.write(self.style.WARNING(f"  Deleted {deleted} existing chapters"))

        # Build parent reference map (code -> Chapter object)
        code_to_chapter = {}
        created = 0
        updated = 0
        skipped = 0

        for i, ch_data in enumerate(chapters_data):
            code = ch_data.get('code', '').strip()
            title = ch_data.get('title', '').strip()
            level = ch_data.get('level', 1)

            if not code or not title:
                self.stdout.write(self.style.WARNING(f"  Skipping entry {i+1}: missing code or title"))
                skipped += 1
                continue

            # Determine parent based on code structure (e.g., "1.2.3" -> parent is "1.2")
            parent = None
            if '.' in code:
                parent_code = '.'.join(code.split('.')[:-1])
                parent = code_to_chapter.get(parent_code)

            if dry_run:
                existing = Chapter.objects.filter(book=book, code=code).first()
                if existing:
                    self.stdout.write(f"  [DRY RUN] Would update: {code} {title}")
                    updated += 1
                else:
                    self.stdout.write(f"  [DRY RUN] Would create: {code} {title}")
                    created += 1
                # Store a fake entry for parent resolution
                code_to_chapter[code] = True
            else:
                # Try to find existing chapter by code
                existing = Chapter.objects.filter(book=book, code=code).first()
                
                if existing:
                    # Update existing chapter
                    existing.title = title
                    existing.level = level
                    existing.parent = parent
                    existing.order = i
                    existing.save()
                    code_to_chapter[code] = existing
                    updated += 1
                else:
                    # Create new chapter
                    new_chapter = Chapter.objects.create(
                        book=book,
                        parent=parent,
                        code=code,
                        title=title,
                        level=level,
                        order=i
                    )
                    code_to_chapter[code] = new_chapter
                    created += 1

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS(f'Sync Complete!'))
        self.stdout.write(f'  Created: {created}')
        self.stdout.write(f'  Updated: {updated}')
        self.stdout.write(f'  Skipped: {skipped}')
        if dry_run:
            self.stdout.write(self.style.WARNING('  (DRY RUN - No actual changes made)'))
