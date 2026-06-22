from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import PostForm
from .models import Post


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
        form = PostForm(request.POST, request.FILES)
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
        form = PostForm(request.POST, request.FILES, instance=post)
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

