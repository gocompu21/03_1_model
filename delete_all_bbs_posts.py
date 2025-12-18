import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from bbs.models import Post


def delete_all_posts():
    count = Post.objects.count()
    if count > 0:
        Post.objects.all().delete()
        print(f"Successfully deleted {count} posts.")
    else:
        print("No posts found to delete.")


if __name__ == "__main__":
    delete_all_posts()
