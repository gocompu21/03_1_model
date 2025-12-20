from django.db import models
from django.contrib.auth.models import User


class PostType(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="유형")

    def __str__(self):
        return self.name


class Post(models.Model):
    type = models.ForeignKey(
        PostType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="게시글 유형",
    )
    title = models.CharField(max_length=200, verbose_name="제목")
    content = models.TextField(verbose_name="내용")
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name="작성자", related_name="bbs_posts"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="작성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    hits = models.PositiveIntegerField(default=0, verbose_name="조회수")

    def __str__(self):
        return self.title


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    content = models.TextField(verbose_name="내용")
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="작성자",
        related_name="bbs_comments",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="작성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    def __str__(self):
        return f"{self.author} - {self.content[:20]}"

    class Meta:
        ordering = ["-created_at"]
