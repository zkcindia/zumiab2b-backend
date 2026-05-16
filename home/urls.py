from django.contrib import admin
from django.urls import path
from home import views
from home.views import *
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.http import JsonResponse

urlpatterns = [
    path('signup/',views.signup),
    path('login/', views.login, name='login'),
    path('login-otp-verify/',views.login_otp_verify),
    path('resend-otp/',views.resend_otp),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)