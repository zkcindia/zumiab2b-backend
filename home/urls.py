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
    path('publish-products/', product_list),
    path('products/filter/', ProductPriceFilterAPIView.as_view(),name='product-price-filter'),    ########
    path('products/bulk-import/',BulkProductImportAPIView.as_view(),name='bulk-product-import'), ############
    path('products/list/', views.ProductListAPIView.as_view(), name='product-list'), #################
    path('orders/', views.order_list, name='order-list'),
    path('order-status/', order_status_list, name='order_status_list'),
    path('status-wise-orders/', views.status_wise_order_list, name='status-wise-orders'),
    path('order-status-count/',order_status_count,name='order_status_count'),
    # path('customer-count/', customer_count, name='customer_count'),
    path('customer-status-count/', customer_status_count, name='customer_status_count'),
    path('product-count/', product_count, name='product_count'),
    path('order-status-summary/', order_status_summary, name='order_status_summary'),
    path('customer-status-summary/',customer_status_summary,name='customer_status_summary'),
    path('delivered-order-summary/',delivered_order_summary,name='delivered_order_summary'),

    path("orders/<int:order_id>/status/",update_order_status,name="update_order_status"),

    path('export-customers/', views.export_customers, name='export-customers'),

    path('cart/', get_cart, name='get-cart'),
    path('add_to_cart/', add_to_cart),

    path('cart/update/', update_cart_quantity, name='update_cart_quantity'),
    path('cart/delete/<int:cart_item_id>/', views.delete_cart_item),

    path('add-message/', add_message, name='add_message'),

    path('address/', address_api, name='address_api'),
    path('address/<slug:slug>/', address_api, name='address_detail'),
    path("delete-address/<int:id>/", delete_address),
    path("default-address/<int:user_id>/", get_default_address),
    path('edit-address/<int:address_id>/', edit_address),
    path("change-status/", change_default_status),
    path('price-range/', product_list_api, name='product_list_api'),

    path("place-order/", place_order, name="place_order"),
    path("buy-now/", buy_now, name="buy_now"),
    path("create-upi-order/",create_upi_order,name="create_upi_order"),
    path("my-upi-orders/",my_upi_orders,name="my_upi_orders"),

    path("upi-orders-by-date/",upi_orders_by_date,name="upi_orders_by_date"),

    path("my-orders/", my_orders),

    path('upi-order/<int:order_id>/status-change/',upi_order_status_change,name='upi-order-status-change'),
    path('pending-upi-order-count/',pending_upi_order_count,name='pending-upi-order-count'),
    path('upi-orders/', views.upi_orders, name='upi-orders'),

    path('public-products-list/', PublicProductListAPIView.as_view()),
    path('products-by-date/', OrderDateFilterAPIView.as_view()),

    path("cart-item-count/", get_cart_item_count, name="cart-item-count"),
    path('order-filter/', OrderFilterAPIView.as_view()),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)