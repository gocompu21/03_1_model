import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from practice.models import Chapter

def inspect(chapter_id):
    try:
        c = Chapter.objects.get(id=chapter_id)
        print(f"Chapter: {c.title} (ID: {c.id})")
        
        if hasattr(c, 'content'):
            content = c.content.content
            length = len(content)
            print(f"Content Length: {length} chars")
            
            base64_count = content.count("data:image")
            print(f"Base64 Images: {base64_count}")
            
            img_tags = content.count("<img")
            print(f"Total <img> tags: {img_tags}")
            
            # Check if separated (heuristic: small content or external links)
            if length > 100000 and base64_count > 0:
                print(">> NOT Separated: Contains large embedded Base64 images.")
            elif length > 100000:
                print(">> Large Text Content.")
            else:
                print(">> Likely Clean/Separated.")
        else:
            print("No Content.")
            
    except Chapter.DoesNotExist:
        print("Chapter not found.")

if __name__ == "__main__":
    inspect(11)
