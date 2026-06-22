from uuid import uuid4

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import PostForm
from .models import Post

MAX_IMAGE_SIZE = 5 * 1024 * 1024
IMAGE_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}


def _matches_image_signature(content_type, header):
    signatures = {
        "image/jpeg": header.startswith(b"\xff\xd8\xff"),
        "image/png": header.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/gif": header.startswith((b"GIF87a", b"GIF89a")),
        "image/webp": header.startswith(b"RIFF") and header[8:12] == b"WEBP",
    }
    return signatures.get(content_type, False)


@login_required
def post_list(request):
    posts = Post.objects.select_related("author")
    return render(request, "community/post_list.html", {"posts": posts})


@login_required
def post_detail(request, pk):
    post = get_object_or_404(Post.objects.select_related("author"), pk=pk)
    return render(request, "community/post_detail.html", {"post": post})


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
