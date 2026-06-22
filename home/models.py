from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.models import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils.text import slugify
import uuid

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()  # OTP users won't need password

        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=20, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(unique=True)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    image = models.ImageField(upload_to='avtar/', default='avtar/avtar.png', blank=True, null=True)
    business_name = models.CharField(max_length=200, blank=True, null=True)
    business_category = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('account', 'Account'),
        ('manager', 'Manager'),
        ('user', 'User'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.email} ({self.role})"
    


class Category(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    slug = models.SlugField(unique=True,blank=True,null=True)
    PUBLISH_CHOICES = [
        ('Publish', 'Publish'),
        ('Unpublish', 'Unpublish')
    ]
    status = models.CharField(choices=PUBLISH_CHOICES, max_length=10, default='Unpublish')
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        blank=True,
        null=True
    )
    
    def save(self, *args, **kwargs):

        # AUTO GENERATE SLUG
        if not self.slug and self.name:
            self.slug = slugify(self.name)

        # AUTO GENERATE TAG ID
        # if not self.tagid:
        #     self.tagid = "CAT" + str(uuid.uuid4().hex[:8]).upper()

        super(Category, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.name)

class Brand(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    slug = models.SlugField(unique=True, blank=True, null=True)

    PUBLISH_CHOICES = [
        ('Publish', 'Publish'),
        ('Unpublish', 'Unpublish')
    ]

    status = models.CharField(
        choices=PUBLISH_CHOICES,
        max_length=10,
        default='Unpublish'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = slugify(self.name)

        super(Brand, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.name)
    

class Product(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True,blank=True,null=True)
    item_code = models.CharField(max_length=100, unique=True)
    brand = models.ForeignKey(Brand,on_delete=models.SET_NULL,null=True,blank=True)
    description = models.TextField(null=True, blank=True)
    category = models.ForeignKey(Category,on_delete=models.SET_NULL,null=True,blank=True)
    mrp = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    retail = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    b2b = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    sku = models.CharField(max_length=100, null=True, blank=True)

    stock_quantity = models.IntegerField(default=0)
    min_order_qty = models.IntegerField(default=1)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    PUBLISH_CHOICES = [
        ('Publish', 'Publish'),
        ('Unpublish', 'Unpublish')
    ]
    
    status = models.CharField(choices=PUBLISH_CHOICES,max_length=10,default='Publish')
    is_best_seller = models.BooleanField(default=False)
    is_available_on_order = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):

        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)
    
    
class ProductImage(models.Model):
    product = models.ForeignKey(Product,on_delete=models.CASCADE,related_name="images")
    image = models.ImageField(upload_to="products/")

    def __str__(self):
        return str(self.id)
    
from django.conf import settings

class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)

    def _str_(self):
        return f"Cart - {self.user.email}"
    

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    def _str_(self):
        return f"{self.product.name} - {self.quantity}"
    
class Message(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message
    
    
class Address(models.Model):
    user = models.ForeignKey( User, on_delete=models.CASCADE,related_name='addresses')
    slug = models.SlugField(unique=True, blank=True, null=True)
    full_name = models.CharField(max_length=100)
    mobile_number = models.CharField(max_length=15)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name
    
class Order(models.Model):
    PAYMENT_CHOICES = (
        ('COD', 'Cash On Delivery'),
        ('UPI',  'UPI')
    )
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Confirmed', 'Confirmed'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='orders')
    address = models.ForeignKey(Address,on_delete=models.SET_NULL,null=True)
    total_amount = models.DecimalField(max_digits=10,decimal_places=2)
    payment_method = models.CharField(max_length=20,choices=PAYMENT_CHOICES,default='COD')
    payment_status = models.BooleanField(default=False)
    order_status = models.CharField(max_length=20,choices=STATUS_CHOICES,default='Pending')
    
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    transaction_screenshot = models.ImageField(upload_to='transactions/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id}"
    
class OrderItem(models.Model):
    order = models.ForeignKey(Order,on_delete=models.CASCADE,related_name='items')
    product = models.ForeignKey(Product,on_delete=models.SET_NULL,null=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10,decimal_places=2)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"