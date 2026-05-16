from django.contrib import admin
from .models import User
from django.contrib.auth.admin import UserAdmin

# admin.site.register(AdminUser, UserAdmin)

@admin.register(User)
class AdminUser(admin.ModelAdmin):
    list_display = ['id','username','phone','email','otp_code','image','role','is_active','created_at']