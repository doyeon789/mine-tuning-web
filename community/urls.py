from django.urls import path

from . import views

app_name = "community"

urlpatterns = [
    path("", views.post_list, name="post_list"),
    path("new/", views.post_create, name="post_create"),
    path("<int:pk>/", views.post_detail, name="post_detail"),
    path("<int:pk>/like/", views.post_like, name="post_like"),
    path("<int:pk>/comments/", views.comment_create, name="comment_create"),
    path("<int:pk>/edit/", views.post_update, name="post_update"),
    path("<int:pk>/delete/", views.post_delete, name="post_delete"),
]
