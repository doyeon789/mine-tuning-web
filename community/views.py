from uuid import uuid4

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.files.storage import default_storage
from django.db.models import Count, F, IntegerField
from django.db.models.expressions import ExpressionWrapper
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CommentForm, PostForm
from .models import Comment, Post

MAX_IMAGE_SIZE = 5 * 1024 * 1024
IMAGE_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}
POPULAR_PERIODS = {
    "realtime": {
        "label": "실시간",
        "duration": timedelta(hours=24),
    },
    "weekly": {
        "label": "주간 인기글",
        "duration": timedelta(days=7),
    },
    "monthly": {
        "label": "월간 인기글",
        "duration": timedelta(days=30),
    },
    "yearly": {
        "label": "연간 인기글",
        "duration": timedelta(days=365),
    },
}
DEFAULT_POPULAR_PERIOD = "realtime"


def _matches_image_signature(content_type, header):
    signatures = {
        "image/jpeg": header.startswith(b"\xff\xd8\xff"),
        "image/png": header.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/gif": header.startswith((b"GIF87a", b"GIF89a")),
        "image/webp": header.startswith(b"RIFF") and header[8:12] == b"WEBP",
    }
    return signatures.get(content_type, False)


def _get_popular_period(period):
    if period in POPULAR_PERIODS:
        return period
    return DEFAULT_POPULAR_PERIOD


def _popular_posts(period):
    period = _get_popular_period(period)
    starts_at = timezone.now() - POPULAR_PERIODS[period]["duration"]
    like_total = Count("liked_users", distinct=True)
    popularity_score = ExpressionWrapper(
        F("view_count") + F("like_total"),
        output_field=IntegerField(),
    )

    return (
        Post.objects.select_related("author")
        .filter(created_at__gte=starts_at)
        .annotate(like_total=like_total)
        .annotate(popularity_score=popularity_score)
        .order_by("-popularity_score", "-like_total", "-created_at", "-pk")
    )


def post_list(request):
    popular_period = _get_popular_period(request.GET.get("popular_period"))
    posts = (
        Post.objects.select_related("author")
        .annotate(like_total=Count("liked_users"))
    )
    return render(
        request,
        "community/post_list.html",
        {
            "posts": posts,
            "popular_posts": _popular_posts(popular_period)[:5],
            "popular_periods": POPULAR_PERIODS,
            "popular_period": popular_period,
        },
    )


def post_detail(request, pk):
    post = get_object_or_404(
        Post.objects.select_related("author").prefetch_related(
            "liked_users",
            "comments__author",
        ),
        pk=pk,
    )
    Post.objects.filter(pk=post.pk).update(view_count=F("view_count") + 1)
    post.refresh_from_db(fields=["view_count"])
    is_liked = (
        request.user.is_authenticated
        and post.liked_users.filter(pk=request.user.pk).exists()
    )
    comment_form = CommentForm()
    return render(
        request,
        "community/post_detail.html",
        {
            "post": post,
            "is_liked": is_liked,
            "comment_form": comment_form,
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
            return redirect("community:post_detail", pk=post.pk)
    else:
        form = PostForm()

    return render(
        request,
        "community/post_form.html",
        {"form": form, "page_title": "글 작성", "submit_label": "등록"},
    )


@login_required
def post_update(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author != request.user:
        raise PermissionDenied

    if request.method == "POST":
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            post = form.save()
            return redirect("community:post_detail", pk=post.pk)
    else:
        form = PostForm(instance=post)

    return render(
        request,
        "community/post_form.html",
        {"form": form, "post": post, "page_title": "글 수정", "submit_label": "저장"},
    )


@require_POST
@login_required
def post_like(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.liked_users.filter(pk=request.user.pk).exists():
        post.liked_users.remove(request.user)
        is_liked = False
    else:
        post.liked_users.add(request.user)
        is_liked = True

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse(
            {
                "is_liked": is_liked,
                "like_count": post.liked_users.count(),
            }
        )
    return redirect("community:post_detail", pk=post.pk)


@require_POST
@login_required
def comment_create(request, pk):
    post = get_object_or_404(Post, pk=pk)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
    return redirect("community:post_detail", pk=post.pk)


@require_POST
@login_required
def comment_update(request, pk, comment_pk):
    comment = get_object_or_404(Comment, pk=comment_pk, post_id=pk)
    if comment.author != request.user:
        raise PermissionDenied

    form = CommentForm(request.POST, instance=comment)
    if form.is_valid():
        form.save()
    return redirect("community:post_detail", pk=pk)


@require_POST
@login_required
def comment_delete(request, pk, comment_pk):
    comment = get_object_or_404(Comment, pk=comment_pk, post_id=pk)
    if comment.author != request.user:
        raise PermissionDenied

    comment.delete()
    return redirect("community:post_detail", pk=pk)


@require_POST
@login_required
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author != request.user:
        raise PermissionDenied

    post.delete()
    return redirect("community:post_list")


@require_POST
@login_required
def markdown_image_upload(request):
    image = request.FILES.get("image")
    if image is None:
        return JsonResponse({"error": "이미지 파일이 필요합니다."}, status=400)

    extension = IMAGE_EXTENSIONS.get(image.content_type)
    if extension is None:
        return JsonResponse(
            {"error": "PNG, JPEG, GIF, WEBP 이미지만 업로드할 수 있습니다."},
            status=400,
        )

    if image.size > MAX_IMAGE_SIZE:
        return JsonResponse(
            {"error": "이미지는 최대 5MB까지 업로드할 수 있습니다."},
            status=413,
        )

    header = image.read(12)
    image.seek(0)
    if not _matches_image_signature(image.content_type, header):
        return JsonResponse({"error": "올바른 이미지 파일이 아닙니다."}, status=400)

    file_name = (
        f"community/markdown/{request.user.pk}/{uuid4().hex}.{extension}"
    )
    saved_name = default_storage.save(file_name, image)
    return JsonResponse({"url": default_storage.url(saved_name)})
