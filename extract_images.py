"""
Script to extract Base64 images from ChapterContent and save to media files.
Usage: python manage.py shell < extract_images.py
"""
import os
import re
import base64
import hashlib
from django.conf import settings
from practice.models import ChapterContent

# Output directory
IMAGES_DIR = os.path.join(settings.MEDIA_ROOT, 'chapter_content')
os.makedirs(IMAGES_DIR, exist_ok=True)

# Pattern to find Base64 images
IMG_PATTERN = re.compile(
    r'<img([^>]*?)src="data:image/([^;]+);base64,([^"]+)"([^>]*?)>',
    re.IGNORECASE | re.DOTALL
)

def extract_images():
    contents = ChapterContent.objects.all()
    total_images = 0
    updated_contents = 0
    
    for content in contents:
        original = content.content
        new_content = original
        images_in_content = 0
        
        for match in IMG_PATTERN.finditer(original):
            pre_attrs = match.group(1)
            img_type = match.group(2)
            b64_data = match.group(3)
            post_attrs = match.group(4)
            
            try:
                # Decode Base64
                img_data = base64.b64decode(b64_data)
                
                # Generate filename
                img_hash = hashlib.md5(img_data).hexdigest()[:12]
                filename = f"chapter_{content.chapter.id}_{img_hash}.{img_type}"
                filepath = os.path.join(IMAGES_DIR, filename)
                
                # Save file
                with open(filepath, 'wb') as f:
                    f.write(img_data)
                
                # Replace in content
                media_url = f"{settings.MEDIA_URL}chapter_content/{filename}"
                new_img_tag = f'<img{pre_attrs}src="{media_url}"{post_attrs}>'
                new_content = new_content.replace(match.group(0), new_img_tag, 1)
                
                images_in_content += 1
                total_images += 1
                print(f"  Saved: {filename}")
                
            except Exception as e:
                print(f"  Error: {e}")
        
        if images_in_content > 0:
            content.content = new_content
            content.save()
            updated_contents += 1
            print(f"Chapter {content.chapter.id}: {images_in_content} images extracted")
    
    print(f"\n" + "="*50)
    print(f"Done! Extracted {total_images} images from {updated_contents} contents.")

if __name__ == "__main__":
    extract_images()
