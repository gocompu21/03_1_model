import os
import django
import sys

# Setup Django Environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User
from bbs.models import Post


def test_create_post():
    try:
        user = User.objects.first()
        if not user:
            print("Error: No users found in database.")
            return

        print(f"Using user: {user.username}")

        user_input = "Test Question for Debug"
        response_text = "<p>Test Answer</p>"

        post = Post.objects.create(
            author=user,
            title=f"[나무주치의] {user_input}"[:200],
            content=str(response_text),
        )
        print(f"Success! Created Post ID: {post.pk}")
        print(f"Title: {post.title}")
    except Exception as e:
        print(f"Failed to create post: {e}")


if __name__ == "__main__":
    test_create_post()
