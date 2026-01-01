from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db.models import Q
from django.core.paginator import Paginator
from django.conf import settings
from .models import Post, Comment
from .forms import PostForm, CommentForm
import os
import uuid
from datetime import datetime


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

    # Capture query params to persist sidebar state and list navigation
    query = request.GET.get("q", "")
    category = request.GET.get("category", "ALL")

    # Filter posts for the list at the bottom (Same logic as post_list)
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

    related_posts = posts.filter(pk__lt=post.pk)[:10]

    # Increment View Count (simple logic)
    # Using cookie to prevent refresh spam could be better, but keeping it simple for now
    post.hits += 1
    post.save()

    comment_form = CommentForm()

    return render(
        request,
        "bbs/post_detail.html",
        {
            "post": post,
            "comment_form": comment_form,
            "query": query,
            "category": category,
            "related_posts": related_posts,
        },
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


@login_required
def image_upload(request):
    """Handle image upload from Summernote editor."""
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)
    
    if not request.FILES.get("file"):
        return JsonResponse({"error": "No file uploaded"}, status=400)
    
    uploaded_file = request.FILES["file"]
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if uploaded_file.content_type not in allowed_types:
        return JsonResponse({"error": "Invalid file type"}, status=400)
    
    # Create upload directory
    upload_dir = os.path.join(settings.MEDIA_ROOT, "bbs", "images")
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        ext = ".jpg"
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    filename = f"bbs_{timestamp}_{unique_id}{ext}"
    filepath = os.path.join(upload_dir, filename)
    
    # Save file
    with open(filepath, "wb+") as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)
    
    # Return URL
    image_url = f"{settings.MEDIA_URL}bbs/images/{filename}"
    return JsonResponse({"url": image_url})
