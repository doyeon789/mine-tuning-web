from django.contrib import admin

from .models import Comment, Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "view_count", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("title", "content", "author__username")
    readonly_fields = ("view_count",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("post", "author", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("content", "author__username", "post__title")
