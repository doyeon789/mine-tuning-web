from django.urls import path

from . import views

app_name = "community"

urlpatterns = [
    path("", views.post_list, name="post_list"),
    path("new/", views.post_create, name="post_create"),
    path(
        "images/upload/",
        views.markdown_image_upload,
        name="markdown_image_upload",
    ),
    path("<int:pk>/", views.post_detail, name="post_detail"),
    path("<int:pk>/like/", views.post_like, name="post_like"),
    path("<int:pk>/comments/", views.comment_create, name="comment_create"),
    path(
        "<int:pk>/comments/<int:comment_pk>/edit/",
        views.comment_update,
        name="comment_update",
    ),
    path(
        "<int:pk>/comments/<int:comment_pk>/delete/",
        views.comment_delete,
        name="comment_delete",
    ),
    path("<int:pk>/edit/", views.post_update, name="post_update"),
    path("<int:pk>/delete/", views.post_delete, name="post_delete"),
]
