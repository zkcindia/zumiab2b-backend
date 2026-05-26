from django.contrib import admin
from .models import User
from django.contrib.auth.admin import UserAdmin
from django.contrib import admin
from .models import *

@admin.register(User)
class AdminUser(admin.ModelAdmin):
    list_display = ['id','username','phone','email','otp_code','image','business_name','business_category','role','status','is_active','created_at']

@admin.register(Category)
class Category(admin.ModelAdmin):
    list_display = ['id','name','slug','created_at']

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'slug', 'status', 'created_at']
    
@admin.register(Product)
class Product(admin.ModelAdmin):
    list_display = ['id','name','slug','status','item_code','brand','description','category','mrp','retail','b2b','sku','stock_quantity','min_order_qty','image','is_best_seller','is_available_on_order','is_active','created_at']


@admin.register(ProductImage)
class ProductImage(admin.ModelAdmin):
    list_display = ['id','product','image']