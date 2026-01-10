import os
import django
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import Chapter

def check_img_src(chapter_id):
    try:
        c = Chapter.objects.get(id=chapter_id)
        if not hasattr(c, 'content'):
            print("No content.")
            return

        content = c.content.content
        # Simple regex to find img src
        imgs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', content)
        
        print(f"Chapter {chapter_id} Images: {len(imgs)}")
        for i, src in enumerate(imgs):
            print(f"[{i+1}] {src[:100]}...")

    except Chapter.DoesNotExist:
        print("Chapter not found.")

if __name__ == "__main__":
    check_img_src(58)
