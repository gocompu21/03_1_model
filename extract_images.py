import os
import django
import re
import base64
import uuid
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import Chapter, ChapterContent

def extract_all_images():
    print("Checking all chapters for embedded images...")
    contents = ChapterContent.objects.all()
    
    total_extracted = 0
    chapters_processed = 0
    
    for content in contents:
        chapter_id = content.chapter.id
        # We can reuse the logic, but let's inline it or call a helper to keep it clean.
        # Logic from extract_images_from_chapter adapted here
        
        html_content = content.content
        if not html_content or 'data:image' not in html_content:
            continue
            
        print(f"Processing Chapter {chapter_id}: {content.chapter.title}")
            
        pattern = re.compile(r'src="data:image/(?P<ext>png|jpeg|jpg|gif|webp);base64,(?P<data>[^"]+)"')
        
        replacement_count = 0
        
        def replace_match(match):
            nonlocal replacement_count
            ext = match.group('ext')
            data_str = match.group('data')
            
            filename = f"chapter_{chapter_id}_{uuid.uuid4().hex[:8]}.{ext}"
            upload_path = f"uploads/content_images/{filename}"
            
            try:
                img_data = base64.b64decode(data_str)
                saved_path = default_storage.save(upload_path, ContentFile(img_data))
                url = default_storage.url(saved_path)
                replacement_count += 1
                return f'src="{url}"'
            except Exception as e:
                print(f"  Error saving image: {e}")
                return match.group(0)

        new_content, count = pattern.subn(replace_match, html_content)
        
        if count > 0:
            content.content = new_content
            content.save()
            print(f"  -> Extracted {count} images. Size reduced: {len(html_content)} -> {len(new_content)}")
            total_extracted += count
            chapters_processed += 1
            
    print(f"\nCompleted! Processed {chapters_processed} chapters, extracted {total_extracted} images total.")

if __name__ == "__main__":
    extract_all_images()
