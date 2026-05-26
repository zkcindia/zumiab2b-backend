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

from .views import category

urlpatterns = [
    path('signup/',views.signup),
    path('login/', views.login, name='login'),
    path('login-otp-verify/',views.login_otp_verify),
    path('resend-otp/',views.resend_otp),
    
    
    path('category/', category),
    path('category/<slug:slug>/', category),
    path('category/status/<slug:slug>/', category_status_change),
    path('publish-category/', publish_category),
    path('publish-category/<slug:slug>/', publish_category),
    # path('category-list/', category_list_api),
    
    path('brand/', brand),
    path('brand/<slug:slug>/', brand),
    path('brand/status/<slug:slug>/', brand_status_change),
    path('publish-brand/', publish_brand),
    path('publish-brand/<slug:slug>/', publish_brand),
    path("product/", product_api),          # GET all + POST
    # path("product/<int:pk>/", product_api), # GET one + PUT + DELETE
    path("product/<slug:slug>/", product_api),
    path('product-status/<slug:slug>/', product_status_api, name='product-status-api'),
    path('publish-products/', product_list_api),
    path('export-customers/', views.export_customers, name='export-customers'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)