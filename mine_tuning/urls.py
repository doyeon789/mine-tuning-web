from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('oauth/', include('allauth.urls')),
    path('', include('mine_chat.urls')),
]
