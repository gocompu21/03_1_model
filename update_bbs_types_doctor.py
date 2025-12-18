import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from bbs.models import Post, PostType


def update_types():
    # 1. Update PostType
    try:
        pt = PostType.objects.get(name="주치의 질의")
        pt.name = "주치의"
        pt.save()
        print("Updated PostType '주치의 질의' to '주치의'")
    except PostType.DoesNotExist:
        if PostType.objects.filter(name="주치의").exists():
            print("PostType '주치의' already exists.")
        else:
            PostType.objects.create(name="주치의")
            print("Created PostType '주치의'")

    # 2. Update Post titles
    # Prefix was "[나무주치의]" (7 chars)
    posts = Post.objects.filter(title__startswith="[나무주치의]")
    count = 0
    for post in posts:
        remaining = post.title[7:].strip()
        post.title = f"[주치의] {remaining}"
        post.save()
        count += 1

    print(f"Updated {count} posts' titles from '[나무주치의]...' to '[주치의]...'")


if __name__ == "__main__":
    update_types()
