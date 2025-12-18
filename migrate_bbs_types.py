import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from bbs.models import Post, PostType


def migrate_types():
    # 1. Create PostTypes
    type_book, _ = PostType.objects.get_or_create(name="기본서 질의")
    type_doctor, _ = PostType.objects.get_or_create(name="주치의 질의")
    type_general, _ = PostType.objects.get_or_create(name="일반 질의")

    print(f"PostTypes created/verified: {type_book}, {type_doctor}, {type_general}")

    # 2. Update existing Posts
    posts = Post.objects.all()
    count_book = 0
    count_doctor = 0
    count_general = 0

    for post in posts:
        if post.title.startswith("[기본서 질의]"):
            post.type = type_book
            count_book += 1
        elif post.title.startswith("[나무주치의]"):
            post.type = type_doctor
            count_doctor += 1
        else:
            # Default to General for all others
            post.type = type_general
            count_general += 1
        post.save()

    print(f"Migration Complete.")
    print(f"Book Queries: {count_book}")
    print(f"Doctor Queries: {count_doctor}")
    print(f"General Queries: {count_general}")


if __name__ == "__main__":
    migrate_types()
