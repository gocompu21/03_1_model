"""
기존 BBS 게시글 제목에서 접두사([주치의], [기본서] 등)를 제거하는 스크립트

사용법:
    python manage.py shell < remove_title_prefix.py

또는:
    python remove_title_prefix.py
"""

import os
import sys
import re

# Django 설정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from bbs.models import Post


def remove_title_prefixes():
    """제목에서 접두사 패턴을 제거"""

    # 제거할 접두사 패턴 목록
    prefixes = [
        r"^\[주치의\]\s*",
        r"^\[나무주치의\]\s*",
        r"^\[기본서\]\s*",
        r"^\[기본서 질의\]\s*",
        r"^\[생리학\]\s*",
        r"^\[병리학\]\s*",
        r"^\[해충학\]\s*",
        r"^\[토양학\]\s*",
        r"^\[관리학\]\s*",
        r"^\[농약학\]\s*",
    ]

    # 모든 패턴을 하나의 정규식으로 결합
    combined_pattern = re.compile("|".join(prefixes))

    posts = Post.objects.all()
    total = posts.count()
    updated = 0

    print(f"총 {total}개 게시글 검사 중...")
    print("-" * 50)

    for post in posts:
        original_title = post.title
        new_title = combined_pattern.sub("", original_title).strip()

        if original_title != new_title:
            print(f"[{post.pk}] '{original_title}' → '{new_title}'")
            post.title = new_title
            post.save(update_fields=["title"])
            updated += 1

    print("-" * 50)
    print(f"완료: {updated}개 게시글 제목 수정됨")

    return updated


if __name__ == "__main__":
    remove_title_prefixes()
