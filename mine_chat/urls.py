from django.urls import path

from . import views

app_name = 'mine_chat'

urlpatterns = [
    path('', views.index, name='index'),
    path('chats/new/', views.session_create, name='session_create'),
    path('chats/<int:pk>/', views.session_detail, name='session_detail'),
    path('chats/<int:pk>/edit/', views.session_update, name='session_update'),
    path('chats/<int:pk>/delete/', views.session_delete, name='session_delete'),
    path('chats/<int:pk>/messages/', views.message_create, name='message_create'),
    path('messages/<int:pk>/edit/', views.message_update, name='message_update'),
]
