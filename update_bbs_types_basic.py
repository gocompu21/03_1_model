import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from bbs.models import Post, PostType


def update_types():
    # 1. Update PostType name
    try:
        pt = PostType.objects.get(name="기본서 질의")
        pt.name = "기본서"
        pt.save()
        print("Updated PostType '기본서 질의' to '기본서'")
    except PostType.DoesNotExist:
        # Check if "기본서" already exists
        if PostType.objects.filter(name="기본서").exists():
            print("PostType '기본서' already exists.")
        else:
            # Create if neither exists (shouldn't happen for migration but safe fallback)
            PostType.objects.create(name="기본서")
            print("Created PostType '기본서'")

    # 2. Update Post titles (only if they start with old prefix)
    posts = Post.objects.filter(title__startswith="[기본서 질의]")
    count = 0
    for post in posts:
        # Replace prefix "[기본서 질의]" (8 chars) with "[기본서]"
        # Check carefully to avoid double brackets if logic was weird
        remaining = post.title[8:].strip()  # " 내용..."
        post.title = f"[기본서] {remaining}"
        post.save()
        count += 1

    print(f"Updated {count} posts' titles from '[기본서 질의]...' to '[기본서]...'")


if __name__ == "__main__":
    update_types()
