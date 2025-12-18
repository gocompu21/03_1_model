from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Post, Comment
from .forms import PostForm, CommentForm


def post_list(request):
    query = request.GET.get("q", "")
    page_number = request.GET.get("page", 1)
    category = request.GET.get("category", "ALL")

    posts = Post.objects.all().order_by("-created_at")

    if category == "BOOK":
        posts = posts.filter(type__name="기본서")
    elif category == "DOCTOR":
        posts = posts.filter(type__name="주치의")
    elif category == "GENERAL":
        posts = posts.filter(type__name="일반 질의")

    if query:
        posts = posts.filter(
            Q(title__icontains=query)
            | Q(content__icontains=query)
            | Q(author__username__icontains=query)
        )

    paginator = Paginator(posts, 15)
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "bbs/post_list.html",
        {"page_obj": page_obj, "query": query, "category": category},
    )


def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)

    # Increment View Count (simple logic)
    # Using cookie to prevent refresh spam could be better, but keeping it simple for now
    post.hits += 1
    post.save()

    comment_form = CommentForm()

    return render(
        request, "bbs/post_detail.html", {"post": post, "comment_form": comment_form}
    )


@login_required
def post_create(request):
    if request.method == "POST":
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect("bbs:post_detail", pk=post.pk)
    else:
        form = PostForm()

    return render(request, "bbs/post_form.html", {"form": form, "title": "글 쓰기"})


@login_required
def post_update(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author != request.user:
        return redirect("bbs:post_detail", pk=post.pk)  # Or 403

    if request.method == "POST":
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            return redirect("bbs:post_detail", pk=post.pk)
    else:
        form = PostForm(instance=post)

    return render(request, "bbs/post_form.html", {"form": form, "title": "글 수정"})


@login_required
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author == request.user:
        post.delete()
    return redirect("bbs:post_list")


@login_required
def comment_create(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.post = post
            comment.save()
    return redirect("bbs:post_detail", pk=post.pk)


@login_required
def comment_delete(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if comment.author == request.user:
        post_pk = comment.post.pk
        comment.delete()
        return redirect("bbs:post_detail", pk=post_pk)
    return redirect("bbs:post_detail", pk=comment.post.pk)
