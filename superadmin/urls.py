from django.contrib import admin
from django.urls import path, include
from superadmin import views
from superadmin.views import *
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


urlpatterns = [
    # superadmin
    path("all-users/", get_all_users, name='get_all_users'),
    path('update-user-status/<int:user_id>/',update_user_status),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)