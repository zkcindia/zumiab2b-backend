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

    path('orders/', views.order_list, name='order-list'),
    path("orders/<int:order_id>/",views.order_details,name="order-details"),

    path('customer-status-count/', customer_status_count, name='customer_status_count'),
    path('order-status-count/',order_status_count,name='order_status_count'),
    path('order-status-summary/', order_status_summary, name='order_status_summary'),
    path('customer-status-summary/',customer_status_summary,name='customer_status_summary'),
    path('product-count/', product_count, name='product_count'),
    path('delivered-order-summary/',delivered_order_summary,name='delivered_order_summary'),
    path('pending-upi-order-count/',pending_upi_order_count,name='pending-upi-order-count'),
    path("last-order-details/",views.get_last_order_details,name="last-order-details"),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)