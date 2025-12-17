import os
import django
import sys

# Setup Django Environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from notebook.models import NotebookHistory
from bbs.models import Post


def check_latest_entries():
    with open("debug_truncated_out.txt", "w", encoding="utf-8") as f:
        print("--- Checking Specific BBS Post: '토양의 종류' ---", file=f)
        # Using contains to be safer
        post = Post.objects.filter(title__contains="토양의 종류").last()
        if post:
            print(f"ID: {post.id}", file=f)
            print(f"Title: {post.title}", file=f)
            print(f"Content Length: {len(post.content)}", file=f)
            print(f"Content Last 200 chars: {post.content[-200:]}", file=f)
        else:
            print("No matching post found for '토양의 종류'.", file=f)


if __name__ == "__main__":
    check_latest_entries()
