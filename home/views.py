from urllib import request
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser
from django.http import JsonResponse
from django.middleware import csrf
from django.utils import timezone
from .helper import send_forget_password_mail
import json, random
from rest_framework_simplejwt.tokens import RefreshToken
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework import status
from .models import *
import json
from django.core.paginator import Paginator, EmptyPage
from django.utils.text import slugify
# from .models import Product, ProductImage
# from django.db.models import Case, When, Value, IntegerField
from io import StringIO
import csv
from django.http import StreamingHttpResponse, HttpResponse
from django.db import connection
import logging


User = get_user_model()

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def admin_profile(request):

    user = request.user

    if request.method == 'GET':
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "phone": user.phone,
        })

    if request.method == 'PUT':
        username = request.data.get("username", user.username)
        email = request.data.get("email", user.email)
        phone = request.data.get("phone", user.phone)

        user.username = username
        user.email = email
        user.phone = phone
        user.save()

        return Response({
            "message": "Profile updated successfully",
            "username": user.username,
            "email": user.email,
            "phone": user.phone,
        }, status=status.HTTP_200_OK)


@csrf_exempt
def signup(request):
    if request.method != 'POST':
        return JsonResponse(
            {'message': 'Invalid request method'},
            status=405
        )

    try:
        # Get form-data values
        username = request.POST.get('username')
        phone = request.POST.get('mobile')
        email = request.POST.get('email')
        business_name = request.POST.get('business_name')
        gst_number = request.POST.get('gst_number')
        business_category = request.POST.get('business_category')
        image = request.FILES.get('image')

        # Validate email
        if not email:
            return JsonResponse(
                {'message': 'Email is required'},
                status=400
            )

        # Check existing email
        if User.objects.filter(email=email).exists():
            return JsonResponse(
                {'message': 'Email already in use'},
                status=400
            )

        # Generate CSRF token
        csrf_token = csrf.get_token(request)

        # Create user
        user = User.objects.create(
            username=username,
            phone=phone,
            email=email,
            business_name=business_name,
            gst_number =gst_number ,
            business_category=business_category,
            image=image,
            otp_code=None,
            is_active=False,
            role='user'
        )

        # Full image URL
        image_url = (
            request.build_absolute_uri(user.image.url)
            if user.image else None
        )

        return JsonResponse({
            'message': 'Data saved successfully',
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'mobile': user.phone,
            'business_name': user.business_name,
            'gst_number' : user.gst_number,
            'business_category': user.business_category,
            'role': user.role,
            'is_active': user.is_active,
            'csrf_token': csrf_token,
            'image': image_url,
            'permission': ['User']
        }, status=201)

    except Exception as e:
        return JsonResponse({
            'message': 'Something went wrong',
            'error': str(e)
        }, status=500)

@csrf_exempt
def login(request):
    if request.method != 'POST':
        return JsonResponse(
            {'message': 'Invalid request method'},
            status=400
        )

    try:
        jsondata = JSONParser().parse(request)
        email = jsondata.get('email')

        # Validate email
        if not email:
            return JsonResponse(
                {'message': 'Email is required'},
                status=400
            )

        # Check user exists
        try:
            user = User.objects.get(email=email)

        except User.DoesNotExist:
            return JsonResponse(
                {'message': 'Email not exists !!'},
                status=400
            )
        
        # ================= REJECTED =================

        if user.status == 'rejected':

            return JsonResponse(
                {
                    'message': 'Your request has been rejected'
                },
                status=403
            )

        # Check user active or not
        if not user.is_active:
            return JsonResponse(
                {
                    'message': 'Your account is under review. Please wait for admin approval.'
                },
                status=403
            )

        # Generate OTP
        otp_code = generate_otp()

        print("Generated OTP:", otp_code)

        # Save OTP
        user.otp_code = otp_code
        user.save()

        # Send OTP mail
        send_forget_password_mail(email, otp_code)

        return JsonResponse(
            {
                'message': 'OTP sent successfully',
                'email': user.email
            },
            status=200
        )

    except Exception as e:
        return JsonResponse(
            {
                'message': 'Something went wrong',
                'error': str(e)
            },
            status=500
        )

def generate_otp():
    return str(random.randint(1000, 9999))


@csrf_exempt
def login_otp_verify(request):
    if request.method == 'POST':
        jsondata = JSONParser().parse(request)
        otp = jsondata.get('otp')

        if not otp:
            return JsonResponse({'message': 'OTP is required'}, status=400)

        # Get user by OTP
        user = User.objects.filter(otp_code=otp).first()

        if not user:
            return JsonResponse({'message': 'Invalid OTP'}, status=401)

        # Generate JWT Token
        refresh = RefreshToken.for_user(user)

        # Final response
        return JsonResponse({
            'message': 'Login successful',
            'email': user.email,
            'name': user.username,
            'image': user.image.url if user.image else None,
            'permission': user.role,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            # 'addresses': user_addresses
        }, status=200)

    return JsonResponse({'message': 'Invalid request method'}, status=400)


@csrf_exempt
def resend_otp(request):
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            email = data.get('email')

            if not email:
                return JsonResponse({'message': 'Email is required'}, status=400)

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return JsonResponse({'message': 'User not found'}, status=404)

            # Generate and save new OTP
            new_otp = generate_otp()
            user.otp_code = new_otp
            user.save()

            # Send the new OTP
            send_forget_password_mail(email, new_otp)
            print("Resent OTP:", new_otp)

            return JsonResponse({'message': 'OTP resent successfully'})

        except Exception as e:
            return JsonResponse({'message': 'Error occurred', 'error': str(e)}, status=500)

    return JsonResponse({'message': 'Invalid request method'}, status=405)

#################################################  Catgory API  ##########################################################

@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def category(request, slug=None):
    if request.method == 'GET':

        if slug is None:
            categories = Category.objects.all().order_by('-created_at')

            data = [{
                "id": i.id,
                "name": i.name,
                "slug": i.slug,
                "status": i.status,
                "created_at": i.created_at,
            } for i in categories]

            return JsonResponse(data, safe=False)
        try:
            obj = Category.objects.get(slug=slug)

            return JsonResponse({
                "id": obj.id,
                "name": obj.name,
                "slug": obj.slug,
                "status": obj.status,
                "created_at": obj.created_at,
            })

        except Category.DoesNotExist:
            return JsonResponse({"error": "Category not found"}, status=404)

    if request.method == 'POST':
        obj = Category.objects.create(
            name=request.data.get('name')
        )

        return JsonResponse({
            "message": "Category created successfully",
            "id": obj.id
        }, status=201)

    if request.method == 'PUT':
        try:
            obj = Category.objects.get(slug=slug)
            obj.name = request.data.get('name')
            obj.save()

            return JsonResponse({"message": "updated successfully"})

        except Category.DoesNotExist:
            return JsonResponse({"error": "not found"}, status=404)

    if request.method == 'DELETE':
        try:
            obj = Category.objects.get(slug=slug)   
            obj.delete()

            return JsonResponse({"message": "deleted successfully"}, status=200)

        except Category.DoesNotExist:
            return JsonResponse({"error": "not found"}, status=404)

@api_view(['PATCH'])
def category_status_change(request, slug):

    try:
        category = Category.objects.get(slug=slug)

    except Category.DoesNotExist:
        return Response({
            "status": False,
            "message": "Category not found"
        }, status=404)

    status_value = request.data.get('status')

    # VALIDATION
    if status_value not in ['Publish', 'Unpublish']:
        return Response({
            "status": False,
            "message": "Invalid status"
        }, status=400)

    # UPDATE STATUS
    category.status = status_value
    category.save()

    return Response({
        "status": True,
        "message": "Category status updated successfully",
        "data": {
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
            "status": category.status
        }
    })
    
@api_view(['GET'])
def publish_category(request, slug=None):
    if slug is None:
        categories = Category.objects.filter(status="Publish").order_by('-created_at')

        data = [{
            "id": i.id,
            "name": i.name,
            "slug": i.slug,
            "status": i.status,
            "created_at": i.created_at,
        } for i in categories]

        return JsonResponse(data, safe=False)

    try:
        obj = Category.objects.get(slug=slug, status="Publish")

        return JsonResponse({
            "id": obj.id,
            "name": obj.name,
            "slug": obj.slug,
            "status": obj.status,
            "created_at": obj.created_at,
        })

    except Category.DoesNotExist:
        return JsonResponse(
            {"error": "Category not found or not published"},
            status=404
        )
        
######################################################  Brand Api   #######################################################################

@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def brand(request, slug=None):
    if request.method == 'GET':

        if slug is None:
            brands = Brand.objects.all().order_by('-created_at')

            data = [{
                "id": i.id,
                "name": i.name,
                "slug": i.slug,
                "status": i.status,
                "created_at": i.created_at,
            } for i in brands]

            return JsonResponse(data, safe=False)
        try:
            obj = Brand.objects.get(slug=slug)

            return JsonResponse({
                "id": obj.id,
                "name": obj.name,
                "slug": obj.slug,
                "status": obj.status,
                "created_at": obj.created_at,
            })

        except Brand.DoesNotExist:
            return JsonResponse({"error": "Brand not found"}, status=404)
        
    if request.method == 'POST':
        obj = Brand.objects.create(
            name=request.data.get('name')
        )

        return JsonResponse({
            "message": "Brand created successfully",
            "id": obj.id
        }, status=201)

    if request.method == 'PUT':
        try:
            obj = Brand.objects.get(slug=slug)
            obj.name = request.data.get('name')
            obj.save()

            return JsonResponse({
                "message": "updated successfully"
            })

        except Brand.DoesNotExist:
            return JsonResponse({"error": "not found"}, status=404)

    if request.method == 'DELETE':
        try:
            obj = Brand.objects.get(slug=slug)
            obj.delete()

            return JsonResponse({
                "message": "deleted successfully"
            }, status=200)

        except Brand.DoesNotExist:
            return JsonResponse({"error": "not found"}, status=404)    
        
#################################################  status Brand changes ###############################################################

@api_view(['PATCH'])
def brand_status_change(request, slug):

    try:
        brand = Brand.objects.get(slug=slug)

    except Brand.DoesNotExist:
        return Response({
            "status": False,
            "message": "Brand not found"
        }, status=404)

    status_value = request.data.get('status')

    # VALIDATION
    if status_value not in ['Publish', 'Unpublish']:
        return Response({
            "status": False,
            "message": "Invalid status"
        }, status=400)

    # UPDATE STATUS
    brand.status = status_value
    brand.save()

    return Response({
        "status": True,
        "message": "Brand status updated successfully",
        "data": {
            "id": brand.id,
            "name": brand.name,
            "slug": brand.slug,
            "status": brand.status
        }
    })  

#################################################### Brand Publices get api ##############################################################

@api_view(['GET'])
def publish_brand(request, slug=None):

    if slug is None:
        brands = Brand.objects.filter(status="Publish").order_by('-created_at')

        data = [{
            "id": i.id,
            "name": i.name,
            "slug": i.slug,
            "status": i.status,
            "created_at": i.created_at,
        } for i in brands]

        return JsonResponse(data, safe=False)

    try:
        obj = Brand.objects.get(slug=slug, status="Publish")

        return JsonResponse({
            "id": obj.id,
            "name": obj.name,
            "slug": obj.slug,
            "status": obj.status,
            "created_at": obj.created_at,
        })

    except Brand.DoesNotExist:
        return JsonResponse(
            {"error": "Brand not found or not published"},
            status=404
        )
        
################################################## Product API #####################################################################
from django.db.models import Case, When, Value, IntegerField

@api_view(["GET", "POST","PUT","DELETE"])
# @permission_classes([IsAuthenticated])
def product_api(request, slug=None):

    # ================= GET =================
    if request.method == "GET":

        if slug:
            try:
                product = Product.objects.select_related(
                    "brand",
                    "category"
                ).get(slug=slug)

                images = ProductImage.objects.filter(product=product)
                

                return JsonResponse({
                    "status": True,
                    "data": {
                        "id": product.id,
                        "name": product.name,
                        "slug": product.slug,
                        "item_code": product.item_code,

                        "brand": {
                            "id": product.brand.id,
                            "name": product.brand.name
                        } if product.brand else None,

                        "category": {
                            "id": product.category.id,
                            "name": product.category.name
                        } if product.category else None,

                        "description": product.description,
                        "status": product.status,

                        "mrp": str(product.mrp),
                        "retail": str(product.retail),
                        "b2b": str(product.b2b),

                        "sku": product.sku,
                        "stock_quantity": product.stock_quantity,
                        "min_order_qty": product.min_order_qty,

                        # "is_best_seller": product.is_best_seller,/
                        # "is_available_on_order": product.is_available_on_order,
                        "is_active": product.is_active,

                        "images": [
                            request.build_absolute_uri(img.image.url)
                            for img in images
                        ]
                    }
                })

            except Product.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": "Product not found"
                }, status=404)

        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 10))

        products = Product.objects.select_related(
            "brand",
            "category"
        ).annotate(
            status_order=Case(
                When(status="Publish", then=Value(1)),
                When(status="Unpublish", then=Value(2)),
                default=Value(3),
                output_field=IntegerField()
            )
        ).order_by("status_order", "-id")

        paginator = Paginator(products, limit)

        try:
            page_data = paginator.page(page)

        except EmptyPage:
            return JsonResponse({
                "status": False,
                "message": "No data found"
            }, status=404)

        result = []

        for product in page_data:

            images = ProductImage.objects.filter(product=product)

            result.append({
                "id": product.id,
                "name": product.name,
                "slug": product.slug,
                "item_code": product.item_code,

                "brand": {
                    "id": product.brand.id,
                    "name": product.brand.name
                } if product.brand else None,

                "category": {
                    "id": product.category.id,
                    "name": product.category.name
                } if product.category else None,

                "description": product.description,
                "status": product.status,

                "mrp": str(product.mrp),
                "retail": str(product.retail),
                "b2b": str(product.b2b),

                "sku": product.sku,
                "stock_quantity": product.stock_quantity,
                "min_order_qty": product.min_order_qty,

                "images": [
                    request.build_absolute_uri(img.image.url)
                    for img in images
                ]
            })

        return JsonResponse({
            "status": True,
            "total": paginator.count,
            "page": page,
            "limit": limit,
            "data": result
        })

    # ================= POST =================
    if request.method == "POST":

        brand = Brand.objects.filter(
            id=request.data.get("brand")
        ).first()

        category = Category.objects.filter(
            id=request.data.get("category")
        ).first()

        name = request.data.get("name")

        product = Product.objects.create(
            name=name,
            slug=slugify(name),

            item_code=request.data.get("item_code"),

            brand=brand,
            category=category,

            description=request.data.get("description"),

            status=request.data.get("status", "Publish"),

            mrp=request.data.get("mrp") or 0,
            retail=request.data.get("retail") or 0,
            b2b=request.data.get("b2b") or 0,

            sku=request.data.get("sku"),

            stock_quantity=request.data.get("stock_quantity") or 0,
            min_order_qty=request.data.get("min_order_qty") or 1,

            is_best_seller=request.data.get("is_best_seller", False),
            is_available_on_order=request.data.get("is_available_on_order", False),
            is_active=request.data.get("is_active", True),
        )

        image_urls = []

        for image in request.FILES.getlist("images"):

            obj = ProductImage.objects.create(
                product=product,
                image=image
            )

            image_urls.append(
                request.build_absolute_uri(obj.image.url)
            )

        return JsonResponse({
            "status": True,
            "message": "Product created successfully",

            "data": {
                "id": product.id,
                "name": product.name,
                "slug": product.slug,
                "item_code": product.item_code,

                "brand": {
                    "id": product.brand.id,
                    "name": product.brand.name
                } if product.brand else None,

                "category": {
                    "id": product.category.id,
                    "name": product.category.name
                } if product.category else None,

                "description": product.description,
                "status": product.status,

                "mrp": str(product.mrp),
                "retail": str(product.retail),
                "b2b": str(product.b2b),

                "sku": product.sku,
                "stock_quantity": product.stock_quantity,
                "min_order_qty": product.min_order_qty,

                "images": image_urls
            }
        })

    if request.method == "PUT":

        if not pk:
            return JsonResponse({
                "status": False,
                "message": "Product ID required"
            }, status=400)

        try:
            product = Product.objects.get(id=pk)

            data = request.data

            # Foreign Keys
            brand_id = data.get("brand")
            category_id = data.get("category")

            if brand_id:
                product.brand = Brand.objects.filter(id=brand_id).first()

            if category_id:
                product.category = Category.objects.filter(id=category_id).first()

            # Product Fields
            product.name = data.get("name", product.name)
            product.item_code = data.get("item_code", product.item_code)
            product.description = data.get("description", product.description)

            product.mrp = data.get("mrp", product.mrp)
            product.retail = data.get("retail", product.retail)
            product.b2b = data.get("b2b", product.b2b)

            product.sku = data.get("sku", product.sku)
            product.stock_quantity = data.get(
                "stock_quantity",
                product.stock_quantity
            )
            product.min_order_qty = data.get(
                "min_order_qty",
                product.min_order_qty
            )

            product.status = data.get("status", product.status)

            product.is_best_seller = data.get(
                "is_best_seller",
                product.is_best_seller
            )

            product.is_available_on_order = data.get(
                "is_available_on_order",
                product.is_available_on_order
            )

            product.is_active = data.get(
                "is_active",
                product.is_active
            )

            product.save()

            # Add New Images
            for img in request.FILES.getlist("images"):
                ProductImage.objects.create(
                    product=product,
                    image=img
                )

            images = ProductImage.objects.filter(product=product)

            return JsonResponse({
                "status": True,
                "message": "Product updated successfully",
                "data": {
                    "id": product.id,
                    "name": product.name,
                    "slug": product.slug,
                    "item_code": product.item_code,

                    "brand": {
                        "id": product.brand.id,
                        "name": product.brand.name
                    } if product.brand else None,

                    "category": {
                        "id": product.category.id,
                        "name": product.category.name
                    } if product.category else None,

                    "description": product.description,
                    "status": product.status,

                    "mrp": str(product.mrp),
                    "retail": str(product.retail),
                    "b2b": str(product.b2b),

                    "sku": product.sku,
                    "stock_quantity": product.stock_quantity,
                    "min_order_qty": product.min_order_qty,

                    "is_best_seller": product.is_best_seller,
                    "is_available_on_order": product.is_available_on_order,
                    "is_active": product.is_active,

                    "images": [
                        request.build_absolute_uri(i.image.url)
                        for i in images
                    ]
                }
            })

        except Product.DoesNotExist:
            return JsonResponse({
                "status": False,
                "message": "Product not found"
            }, status=404)

    if request.method == "DELETE":

        if not slug:
            return JsonResponse({
                "status": False,
                "message": "Product slug required"
            }, status=400)

        try:
            product = Product.objects.get(slug=slug)

            product.delete()

            return JsonResponse({
                "status": True,
                "message": "Product deleted successfully"
            })

        except Product.DoesNotExist:
            return JsonResponse({
                "status": False,
                "message": "Product not found"
            }, status=404)
        
#################################################  product status changes  #####################################################

@csrf_exempt
def product_status_api(request, slug):
    if request.method == "POST":
        try:
            p = Product.objects.get(slug=slug)

            new_status = request.POST.get("status")

            if not new_status:
                return JsonResponse({
                    "status": False,
                    "message": "Status is required"
                }, status=400)

            if new_status not in ["Publish", "Unpublish"]:
                return JsonResponse({
                    "status": False,
                    "message": "Invalid status"
                }, status=400)

            p.status = new_status
            p.save(update_fields=["status"])

            return JsonResponse({
                "status": True,
                "message": "Status updated successfully",
                "product": {
                    "slug": p.slug,
                    "status": p.status
                }
            })

        except Product.DoesNotExist:
            return JsonResponse({
                "status": False,
                "message": "Product not found"
            }, status=404)
            
####################### product  Publis  list api #############################

# @api_view(['GET'])
# def product_list(request):

#     products = Product.objects.filter(status="Publish").order_by('-id')

#     data = []
#     for p in products:
        
#          # GET MULTIPLE IMAGES
#         product_images = ProductImage.objects.filter(product=p)

#         image_list = []

#         for img in product_images:
#             if img.image:
#                 image_list.append(
#                     request.build_absolute_uri(img.image.url)
#                 )
#         data.append({
#             "id": p.id,
#             "name": p.name,
#             "slug": p.slug,
#             "item_code": p.item_code,
#             "mrp": p.mrp,
#             "retail": p.retail,
#             "b2b": p.b2b,

#             "sku": p.sku,   
#             "status": p.status,
#             "brand": {
#                 "id": p.brand.id,
#                 "name": p.brand.name
#             } if p.brand else None,

#             "category": {
#                 "id": p.category.id,
#                 "name": p.category.name
#             } if p.category else None,
#             "description": p.description,
#             "stock_quantity": p.stock_quantity,
            
#             "min_order_qty": p.min_order_qty,
#             "images": image_list

            
#         })

#     return JsonResponse({
#         "status": True,
#         "total": len(data),
#         "data": data
#     })


@api_view(['GET'])
def product_list(request):

    products = Product.objects.filter(
        status="Publish"
    ).order_by("-id")

    display, _ = DisplaySetting.objects.get_or_create(id=1)

    data = []

    for p in products:

        product_images = ProductImage.objects.filter(product=p)

        image_list = []

        for img in product_images:
            if img.image:
                image_list.append(
                    request.build_absolute_uri(img.image.url)
                )

        product_data = {
            "id": p.id,
            "name": p.name,
            "slug": p.slug,
            "status": p.status,
            "min_order_qty": p.min_order_qty,
            "images": image_list,
        }

        if display.item_code:
            product_data["item_code"] = p.item_code

        if display.mrp:
            product_data["mrp"] = p.mrp

        if display.retail:
            product_data["retail"] = p.retail

        if display.b2b:
            product_data["b2b"] = p.b2b

        if display.sku:
            product_data["sku"] = p.sku

        if display.stock_quantity:
            product_data["stock_quantity"] = p.stock_quantity

        if display.brand:
            product_data["brand"] = (
                {
                    "id": p.brand.id,
                    "name": p.brand.name
                }
                if p.brand else None
            )

        if display.description:
            product_data["description"] = p.description

        # Always visible
        product_data["category"] = (
            {
                "id": p.category.id,
                "name": p.category.name
            }
            if p.category else None
        )

        data.append(product_data)

    return JsonResponse({
        "status": True,
        "total": len(data),
        "data": data
    })


from rest_framework.views import APIView

class ProductPriceFilterAPIView(APIView):

    def get(self, request):

        price_range = request.GET.get('price_range')
        order = request.GET.get('order', 'asc')

        products = Product.objects.filter(is_active=True)

        # Price Filter
        if price_range == '0-1000':
            products = products.filter(retail_gte=0, retail_lte=1000)

        elif price_range == '1000-5000':
            products = products.filter(retail_gt=1000, retail_lte=5000)

        elif price_range == '5000+':
            products = products.filter(retail__gt=5000)

        # Order By
        if order == 'desc':
            products = products.order_by('-retail')
        else:
            products = products.order_by('retail')

        data = list(
            products.values(
                'id',
                'name',
                'item_code',
                'retail',
                'mrp',
                'b2b',
                'stock_quantity',
                'image'
            )
        )

        return Response(data)

import pandas as pd

# class BulkProductImportAPIView(APIView):

#     def post(self, request):

#         excel_file = request.FILES.get('file')

#         if not excel_file:
#             return Response({"error": "Excel file is required"}, status=400)

#         df = pd.read_excel(excel_file)

#         results = []
#         created_count = 0
#         updated_count = 0
#         failed_count = 0

#         for index, row in df.iterrows():

#             row_number = index + 2

#             try:
#                 name = str(row.get('name', '')).strip()
#                 item_code = str(row.get('item_code', '')).strip()

#                 category_name = str(row.get('category', '')).strip()
#                 brand_name = str(row.get('brand', '')).strip()

#                 mrp = row.get('mrp') or 0
#                 retail = row.get('retail') or 0
#                 b2b = row.get('b2b') or 0
#                 stock = row.get('stock') or 0

#                 # ---------------- VALIDATION ----------------
#                 if not name or name == "nan":
#                     raise Exception("Missing name")

#                 if not item_code or item_code == "nan":
#                     raise Exception("Missing item_code")

#                 # ---------------- CATEGORY ----------------
#                 category = None
#                 if category_name and category_name != "nan":
#                     category, _ = Category.objects.get_or_create(
#                         name=category_name
#                     )

#                 # ---------------- BRAND (FIXED) ----------------
#                 brand = None
#                 if brand_name and brand_name != "nan":
#                     slug = slugify(brand_name)

#                     brand, _ = Brand.objects.get_or_create(
#                         slug=slug,
#                         defaults={"name": brand_name}
#                     )

#                 # ---------------- PRODUCT (FIXED LOGIC) ----------------
#                 product, created = Product.objects.get_or_create(
#                     item_code=item_code,
#                     defaults={
#                         "name": name,
#                         "category": category,
#                         "brand": brand,
#                         "mrp": float(mrp),
#                         "retail": float(retail),
#                         "b2b": float(b2b),
#                         "stock_quantity": int(stock)
#                     }
#                 )

#                 if not created:
#                     # UPDATE existing product
#                     product.name = name
#                     product.category = category
#                     product.brand = brand
#                     product.mrp = float(mrp)
#                     product.retail = float(retail)
#                     product.b2b = float(b2b)
#                     product.stock_quantity = int(stock)
#                     product.save()

#                     updated_count += 1

#                     results.append({
#                         "row": row_number,
#                         "status": "success",
#                         "action": "updated",
#                         "item_code": item_code
#                     })

#                 else:
#                     created_count += 1

#                     results.append({
#                         "row": row_number,
#                         "status": "success",
#                         "action": "created",
#                         "item_code": item_code
#                     })

#             except Exception as e:

#                 failed_count += 1

#                 results.append({
#                     "row": row_number,
#                     "status": "failed",
#                     "item_code": str(row.get("item_code", "")),
#                     "reason": str(e)
#                 })

#         return Response({
#             "success": True,
#             "total_rows": len(df),
#             "created_count": created_count,
#             "updated_count": updated_count,
#             "failed_count": failed_count,
#             "results": results
#         })
    
class BulkProductImportAPIView(APIView):

    def post(self, request):

        excel_file = request.FILES.get("file")

        if not excel_file:
            return Response(
                {"error": "Excel file is required"},
                status=400
            )

        df = pd.read_excel(excel_file)

        created_count = 0
        updated_count = 0
        failed_count = 0
        results = []

        for index, row in df.iterrows():

            row_number = index + 2

            try:

                name = str(row.get("name", "")).strip()
                item_code = str(row.get("item_code", "")).strip()

                category_name = str(
                    row.get("category", "")
                ).strip().lower()

                brand_name = str(
                    row.get("brand", "")
                ).strip().lower()

                description = str(
                    row.get("description", "")
                ).strip()

                sku = str(
                    row.get("sku", "")
                ).strip()

                status = str(
                    row.get("status", "Publish")
                ).strip()

                mrp = float(row.get("mrp") or 0)
                retail = float(row.get("retail") or 0)
                b2b = float(row.get("b2b") or 0)

                stock_quantity = int(
                    row.get("stock_quantity") or 0
                )

                min_order_qty = int(
                    row.get("min_order_qty") or 1
                )

                # ---------------- VALIDATION ----------------

                if not name or name == "nan":
                    raise Exception("Missing name")

                if not item_code or item_code == "nan":
                    raise Exception("Missing item_code")

                # ---------------- CATEGORY ----------------

                category = None

                if category_name and category_name != "nan":

                    category, _ = Category.objects.get_or_create(
                        slug=slugify(category_name),
                        defaults={
                            "name": category_name
                        }
                    )

                # ---------------- BRAND ----------------

                brand = None

                if brand_name and brand_name != "nan":

                    brand, _ = Brand.objects.get_or_create(
                        slug=slugify(brand_name),
                        defaults={
                            "name": brand_name
                        }
                    )

                # ---------------- PRODUCT ----------------

                product, created = Product.objects.get_or_create(
                    item_code=item_code,
                    defaults={
                        "name": name,
                        "category": category,
                        "brand": brand,
                        "description": description,
                        "mrp": mrp,
                        "retail": retail,
                        "b2b": b2b,
                        "sku": sku,
                        "stock_quantity": stock_quantity,
                        "min_order_qty": min_order_qty,
                        "status": status,
                    },
                )

                if created:

                    created_count += 1

                    action = "created"

                else:

                    product.name = name
                    product.category = category
                    product.brand = brand
                    product.description = description
                    product.mrp = mrp
                    product.retail = retail
                    product.b2b = b2b
                    product.sku = sku
                    product.stock_quantity = stock_quantity
                    product.min_order_qty = min_order_qty
                    product.status = status

                    product.save()

                    updated_count += 1

                    action = "updated"

                results.append({
                    "row": row_number,
                    "status": "success",
                    "action": action,
                    "item_code": item_code,
                })

            except Exception as e:

                failed_count += 1

                results.append({
                    "row": row_number,
                    "status": "failed",
                    "item_code": str(row.get("item_code", "")),
                    "reason": str(e),
                })

        return Response({
            "success": True,
            "total_rows": len(df),
            "created_count": created_count,
            "updated_count": updated_count,
            "failed_count": failed_count,
            "results": results,
        })


class ProductListAPIView(APIView):

    def get(self, request):

        products = Product.objects.all()

        results = []

        for product in products:

            image_url = None
            if product.image:
                image_url = request.build_absolute_uri(product.image.url)

            results.append({
                "id": product.id,
                "name": product.name,
                "item_code": product.item_code,
                "category": product.category.name if product.category else None,
                "brand": product.brand.name if product.brand else None,
                "mrp": product.mrp,
                "retail": product.retail,
                "b2b": product.b2b,
                "stock_quantity": product.stock_quantity,
                "image": image_url
            })

        return Response({
            "success": True,
            "total_products": len(results),
            "data": results
        })

# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def order_list(request):

#     orders = Order.objects.all().order_by('-id')

#     data = []

#     for order in orders:
#         data.append({
#         "order_id": order.id,
#         "status": order.order_status,
#         "customer_name": order.address.full_name if order.address else "",
#         "business_name": order.user.business_name,
#         "email": order.user.email,
#         "phone": order.user.phone,
#         "total_amount": str(order.total_amount),
#         "payment_method": order.payment_method,
#         "address": {
#             "full_name": order.address.full_name if order.address else "",
#             "mobile_number": order.address.mobile_number if order.address else "",
#             "address_line_1": order.address.address_line_1 if order.address else "",
#             "address_line_2": order.address.address_line_2 if order.address else "",
#             "city": order.address.city if order.address else "",
#             "state": order.address.state if order.address else "",
#             "pincode": order.address.pincode if order.address else "",
#         },
#         "created_at": order.created_at,
#     })

#     return JsonResponse({
#         "total_orders": orders.count(),
#         "data": data
#     })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_list(request):

    orders = Order.objects.all().prefetch_related(
        'items__product',
        'items__product__images'
    ).order_by('-id')

    data = []

    for order in orders:

        products = []

        for item in order.items.all():

            product = item.product

            product_images = []

            if product:
                for img in product.images.all():
                    product_images.append(
                        request.build_absolute_uri(img.image.url)
                    )

            products.append({
                "order_item_id": item.id,
                "quantity": item.quantity,
                "price": str(item.price),

                "product": {
                    "id": product.id if product else None,
                    "name": product.name if product else None,
                    "item_code": product.item_code if product else None,
                    "retail": str(product.retail) if product else None,

                    "image": (
                        request.build_absolute_uri(product.image.url)
                        if product and product.image else None
                    ),

                    "images": product_images
                }
            })

        data.append({
            "order_id": order.id,
            "status": order.order_status,
            "transaction_id": order.transaction_id,
            "customer_name": order.address.full_name if order.address else "",
            "business_name": order.user.business_name,
            "email": order.user.email,
            "phone": order.user.phone,
            "total_amount": str(order.total_amount),
            "payment_method": order.payment_method,

            "address": {
                "full_name": order.address.full_name if order.address else "",
                "mobile_number": order.address.mobile_number if order.address else "",
                "address_line_1": order.address.address_line_1 if order.address else "",
                "address_line_2": order.address.address_line_2 if order.address else "",
                "city": order.address.city if order.address else "",
                "state": order.address.state if order.address else "",
                "pincode": order.address.pincode if order.address else "",
            },

            "products": products,

            "created_at": order.created_at,
        })

    return JsonResponse({
        "total_orders": orders.count(),
        "data": data
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_orders(request):

    orders = Order.objects.filter(
        user=request.user
    ).prefetch_related(
        'items__product',
        'items__product__images'
    ).order_by('-id')

    data = []

    for order in orders:

        products = []

        for item in order.items.all():

            product = item.product

            product_images = []

            if product:
                for img in product.images.all():
                    product_images.append(
                        request.build_absolute_uri(img.image.url)
                    )

            products.append({
                "order_item_id": item.id,
                "quantity": item.quantity,
                "price": str(item.price),

                "product": {
                    "id": product.id if product else None,
                    "name": product.name if product else None,
                    "item_code": product.item_code if product else None,
                    "retail": str(product.retail) if product else None,

                    "image": (
                        request.build_absolute_uri(product.image.url)
                        if product and product.image else None
                    ),

                    "images": product_images
                }
            })

        data.append({
            "order_id": order.id,
            "status": order.order_status,
            "transaction_id": order.transaction_id,
            "customer_name": order.address.full_name if order.address else "",
            "business_name": order.user.business_name,
            "email": order.user.email,
            "phone": order.user.phone,
            "total_amount": str(order.total_amount),
            "payment_method": order.payment_method,

            "address": {
                "full_name": order.address.full_name if order.address else "",
                "mobile_number": order.address.mobile_number if order.address else "",
                "address_line_1": order.address.address_line_1 if order.address else "",
                "address_line_2": order.address.address_line_2 if order.address else "",
                "city": order.address.city if order.address else "",
                "state": order.address.state if order.address else "",
                "pincode": order.address.pincode if order.address else "",
            },

            "products": products,

            "created_at": order.created_at,
        })

    return JsonResponse({
        "total_orders": orders.count(),
        "data": data
    })



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_status_list(request):
    
    statuses = [
        {
            "value": value,
            "label": label
        }
        for value, label in Order.STATUS_CHOICES
    ]

    return JsonResponse({
        "status": True,
        "count": len(statuses),
        "data": statuses
    })

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_order_status(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return JsonResponse({
            "status": False,
            "message": "Order not found"
        }, status=404)
    
    new_status = request.data.get("order_status")

    valid_status = [status[0] for status in Order.STATUS_CHOICES]

    if not new_status:
        return JsonResponse({
            "status": False,
            "message": "Order status is required"
        }, status=400)
    if new_status not in valid_status:
        return JsonResponse({
            "status": False,
            "message": f"Invalid status. Allowed: {valid_status}"
        }, status=400)
    order.order_status = new_status
    order.save()
    return JsonResponse({
        "status": True,
        "message":"Order status updated successfully",
        "data":{
            "order_id": order.id,
            "order_status": order.order_status
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def status_wise_order_list(request):

    order_status = request.GET.get("order_status")
    limit = int(request.GET.get("limit", 10))
    offset = int(request.GET.get("offset", 0))

    orders = Order.objects.select_related(
        "user",
        "address"
    ).order_by("-created_at")

    if order_status:
        orders = orders.filter(order_status=order_status)

    total_count = orders.count()

    orders = orders[offset:offset + limit]

    data = []

    for order in orders:
        data.append({
            "order_id": order.id,
            "customer_name": order.user.get_full_name() if hasattr(order.user, "get_full_name") else "",
            "email": order.user.email,
            "total_amount": str(order.total_amount),
            "payment_method": order.payment_method,
            "payment_status": order.payment_status,
            "order_status": order.order_status,
            "created_at": order.created_at,

            "address": {
                "full_name": order.address.full_name if order.address else None,
                "mobile_number": order.address.mobile_number if order.address else None,
                "address_line_1": order.address.address_line_1 if order.address else None,
                "address_line_2": order.address.address_line_2 if order.address else None,
                "city": order.address.city if order.address else None,
                "state": order.address.state if order.address else None,
                "pincode": order.address.pincode if order.address else None,
            }
        })

    return JsonResponse({
        "status": True,
        "total_orders": total_count,
        "limit": limit,
        "offset": offset,
        "data": data
    })
############################################ count order status api ########################################################################################

from django.db.models import Count


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def order_status_count(request):

#     status_counts = (
#         Order.objects
#         .values('order_status')
#         .annotate(count=Count('id'))
#         .order_by('order_status')
#     )

#     return JsonResponse({
#         "status": True,
#         "data": list(status_counts)
#     })
from django.db.models import Count

# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def order_status_count(request):

#     total_orders = Order.objects.count()

#     status_counts = (
#         Order.objects
#         .values('order_status')
#         .annotate(count=Count('id'))
#         .order_by('order_status')
#     )

#     return JsonResponse({
#         "status": True,
#         "total_orders": total_orders,
#         "data": list(status_counts)
#     })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_status_count(request):

    # Allow only admins
    if request.user.role != "admin":
        return JsonResponse(
            {
                "status": False,
                "message": "Permission denied"
            },
            status=403
        )

    total_orders = Order.objects.count()

    status_counts = (
        Order.objects
        .values('order_status')
        .annotate(count=Count('id'))
        .order_by('order_status')
    )

    return JsonResponse(
        {
            "status": True,
            "total_orders": total_orders,
            "data": list(status_counts)
        }
    )

############################ Costmoer count by status api #######################################################################

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def customer_status_count(request):

#     User = get_user_model()

#     total_customers = User.objects.filter(role='user').count()

#     status_counts = (
#         User.objects
#         .filter(role='user')
#         .values('status')
#         .annotate(count=Count('id'))
#         .order_by('status')
#     )

#     pending_approval = User.objects.filter(
#             role='user',
#             status='pending'
#         ).count()
    
#     return JsonResponse({
#         "status": True,
#         "total_customers": total_customers,
#         "pending_approval": pending_approval,
#         "data": list(status_counts)
#     })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def customer_status_count(request):

    # Allow only admins
    if request.user.role != "admin":
        return JsonResponse(
            {
                "status": False,
                "message": "Permission denied"
            },
            status=403
        )

    User = get_user_model()

    total_customers = User.objects.filter(
        role='user'
    ).count()

    status_counts = (
        User.objects
        .filter(role='user')
        .values('status')
        .annotate(count=Count('id'))
        .order_by('status')
    )

    pending_approval = User.objects.filter(
        role='user',
        status='pending'
    ).count()

    return JsonResponse({
        "status": True,
        "total_customers": total_customers,
        "pending_approval": pending_approval,
        "data": list(status_counts)
    })

 ########################################## product count api ########################################################################################
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import Product

# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def product_count(request):

#     total_products = Product.objects.count()
#     active_products = Product.objects.filter(status='Publish').count()

#     return JsonResponse({
#         "status": True,
#         "total_products": total_products,
#         "active_products": active_products
#     }) 

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def product_count(request):

    # Allow only admins
    if request.user.role != "admin":
        return JsonResponse(
            {
                "status": False,
                "message": "Permission denied"
            },
            status=403
        )

    total_products = Product.objects.count()

    active_products = Product.objects.filter(
        status='Publish'
    ).count()

    return JsonResponse(
        {
            "status": True,
            "total_products": total_products,
            "active_products": active_products
        }
    )

######################################## Percentage order status api ########################################################################################

from .models import Order
# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def order_status_summary(request):

#     total_orders = Order.objects.count()

#     pending = Order.objects.filter(order_status='Pending').count()
#     processing = Order.objects.filter(order_status='Processing').count()
#     shipped = Order.objects.filter(order_status='Shipped').count()
#     delivered = Order.objects.filter(order_status='Delivered').count()
#     cancelled = Order.objects.filter(order_status='Cancelled').count()

#     if total_orders > 0:
#         pending_percent = round((pending / total_orders) * 100, 2)
#         processing_percent = round((processing / total_orders) * 100, 2)
#         shipped_percent = round((shipped / total_orders) * 100, 2)
#         delivered_percent = round((delivered / total_orders) * 100, 2)
#         cancelled_percent = round((cancelled / total_orders) * 100, 2)
#     else:
#         pending_percent = processing_percent = shipped_percent = delivered_percent = cancelled_percent = 0

#     return JsonResponse({
#         "status": True,
#         "total_orders": total_orders,
#         "data": {
#             "Pending": {
#                 "count": pending,
#                 "percentage": pending_percent
#             },
#             "Processing": {
#                 "count": processing,
#                 "percentage": processing_percent
#             },
#             "Shipped": {
#                 "count": shipped,
#                 "percentage": shipped_percent
#             },
#             "Delivered": {
#                 "count": delivered,
#                 "percentage": delivered_percent
#             },
#             "Cancelled": {
#                 "count": cancelled,
#                 "percentage": cancelled_percent
#             }
#         }
#     })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_status_summary(request):

    # Allow only admin users
    if request.user.role != "admin":
        return JsonResponse(
            {
                "status": False,
                "message": "Permission denied"
            },
            status=403
        )

    total_orders = Order.objects.count()

    pending = Order.objects.filter(
        order_status='Pending'
    ).count()

    processing = Order.objects.filter(
        order_status='Processing'
    ).count()

    shipped = Order.objects.filter(
        order_status='Shipped'
    ).count()

    delivered = Order.objects.filter(
        order_status='Delivered'
    ).count()

    cancelled = Order.objects.filter(
        order_status='Cancelled'
    ).count()

    if total_orders > 0:
        pending_percent = round(
            (pending / total_orders) * 100, 2
        )

        processing_percent = round(
            (processing / total_orders) * 100, 2
        )

        shipped_percent = round(
            (shipped / total_orders) * 100, 2
        )

        delivered_percent = round(
            (delivered / total_orders) * 100, 2
        )

        cancelled_percent = round(
            (cancelled / total_orders) * 100, 2
        )

    else:
        pending_percent = 0
        processing_percent = 0
        shipped_percent = 0
        delivered_percent = 0
        cancelled_percent = 0

    return JsonResponse(
        {
            "status": True,
            "total_orders": total_orders,
            "data": {
                "Pending": {
                    "count": pending,
                    "percentage": pending_percent
                },
                "Processing": {
                    "count": processing,
                    "percentage": processing_percent
                },
                "Shipped": {
                    "count": shipped,
                    "percentage": shipped_percent
                },
                "Delivered": {
                    "count": delivered,
                    "percentage": delivered_percent
                },
                "Cancelled": {
                    "count": cancelled,
                    "percentage": cancelled_percent
                }
            }
        }
    )

#################################### Customer status summary api ########################################################################################

# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def customer_status_summary(request):

#     total_customers = User.objects.count()
#     print(total_customers)

#     approved = User.objects.filter(status='approved').count()
#     pending = User.objects.filter(status='pending').count()
#     rejected = User.objects.filter(status='rejected').count()

#     if total_customers > 0:
#         approved_percent = round((approved / total_customers) * 100, 2)
#         pending_percent = round((pending / total_customers) * 100, 2)
#         rejected_percent = round((rejected / total_customers) * 100, 2)
#     else:
#         approved_percent = pending_percent = rejected_percent = 0

#     return JsonResponse({
#         "status": True,
#         "total_customers": total_customers,
#         "data": {
#             "Approved": {
#                 "count": approved,
#                 "percentage": approved_percent
#             },
#             "Pending": {
#                 "count": pending,
#                 "percentage": pending_percent
#             },
#             "Rejected": {
#                 "count": rejected,
#                 "percentage": rejected_percent
#             }
#         }
#     })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def customer_status_summary(request):

    # Allow only admins
    if request.user.role != "admin":
        return JsonResponse(
            {
                "status": False,
                "message": "Permission denied"
            },
            status=403
        )

    total_customers = User.objects.filter(role='user').count()

    approved = User.objects.filter(
        role='user',
        status='approved'
    ).count()

    pending = User.objects.filter(
        role='user',
        status='pending'
    ).count()

    rejected = User.objects.filter(
        role='user',
        status='rejected'
    ).count()

    if total_customers > 0:
        approved_percent = round(
            (approved / total_customers) * 100, 2
        )

        pending_percent = round(
            (pending / total_customers) * 100, 2
        )

        rejected_percent = round(
            (rejected / total_customers) * 100, 2
        )

    else:
        approved_percent = 0
        pending_percent = 0
        rejected_percent = 0

    return JsonResponse(
        {
            "status": True,
            "total_customers": total_customers,
            "data": {
                "Approved": {
                    "count": approved,
                    "percentage": approved_percent
                },
                "Pending": {
                    "count": pending,
                    "percentage": pending_percent
                },
                "Rejected": {
                    "count": rejected,
                    "percentage": rejected_percent
                }
            }
        }
    )


################################### all Delevered Total Amount api ########################################################################################
from django.db.models import Sum
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def delivered_order_summary(request):

#     delivered_orders = Order.objects.filter(order_status='Delivered')

#     total_delivered_orders = delivered_orders.count()

#     total_delivered_amount = delivered_orders.aggregate(
#         total=Sum('total_amount')
#     )['total'] or 0

#     total_customers = delivered_orders.values(
#         'user'
#     ).distinct().count()

#     return JsonResponse({
#         "status": True,
#         "total_delivered_orders": total_delivered_orders,
#         "total_delivered_amount": str(total_delivered_amount),
#         "total_customers": total_customers
#     })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def delivered_order_summary(request):

    # Allow only admins
    if request.user.role != "admin":
        return JsonResponse(
            {
                "status": False,
                "message": "Permission denied"
            },
            status=403
        )

    delivered_orders = Order.objects.filter(
        order_status='Delivered'
    )

    total_delivered_orders = delivered_orders.count()

    total_delivered_amount = delivered_orders.aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    total_customers = delivered_orders.values(
        'user'
    ).distinct().count()

    return JsonResponse(
        {
            "status": True,
            "total_delivered_orders": total_delivered_orders,
            "total_delivered_amount": str(total_delivered_amount),
            "total_customers": total_customers
        }
    )
####################################################  Export api   ##################################################################

logger = logging.getLogger(__name__)


def echo_writer(rows):
    for row in rows:
        buffer = StringIO()
        writer = csv.writer(buffer, quoting=csv.QUOTE_ALL)
        writer.writerow([str(val) for val in row])
        yield buffer.getvalue()
        buffer.close()


def export_customers(request):
    status = request.GET.get('status', 'all')  # all / approved / pending

    valid_status = ['all', 'approved', 'pending']

    if status not in valid_status:
        return HttpResponse("Invalid status", status=400)

    try:
        def generate_rows():
            # CSV Header
            yield ["ID", "Name", "Email", "Status"]

            query = "SELECT id, name, email, status FROM customer_customer"
            params = []

            if status != 'all':
                query += " WHERE status = %s"
                params.append(status)

            with connection.cursor() as cursor:
                cursor.execute(query, params)

                while True:
                    row = cursor.fetchone()
                    if not row:
                        break

                    yield [
                        row[0],  # ID
                        row[1],  # Name
                        row[2],  # Email
                        row[3],  # Status
                    ]

        response = StreamingHttpResponse(
            echo_writer(generate_rows()),
            content_type='text/csv'
        )

        response['Content-Disposition'] = (
            f'attachment; filename="customers_{status}.csv"'
        )

        return response

    except Exception as e:
        logger.error(str(e))
        return HttpResponse(f"Error: {str(e)}", status=500)
    

################################################### Cart #################################################################
from django.shortcuts import get_object_or_404

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def add_to_cart(request):
#     user = request.user

#     product_id = request.data.get("product_id")
#     quantity = int(request.data.get("quantity", 1))

#     if not product_id:
#         return Response({
#             "status": False,
#             "message": "product_id is required"
#         }, status=400)

#     # ======================
#     # GET PRODUCT
#     # ======================
#     product = get_object_or_404(Product, id=product_id)

#     # ======================
#     # CART (USER MUST BE AUTHENTICATED)
#     # ======================
#     cart, _ = Cart.objects.get_or_create(user=user)

#     # ======================
#     # ADD / UPDATE CART ITEM
#     # ======================
#     cart_item, created = CartItem.objects.get_or_create(
#         cart=cart,
#         product=product,
#         defaults={"quantity": quantity}
#     )

#     if not created:
#         cart_item.quantity += quantity

#     cart_item.save()

#     # ======================
#     # PRODUCT IMAGES
#     # ======================
#     images = ProductImage.objects.filter(product=product)

#     image_list = [
#         request.build_absolute_uri(img.image.url)
#         for img in images
#     ]

#     # ======================
#     # RESPONSE
#     # ======================
#     return Response({
#         "status": True,
#         "message": "Product added to cart successfully",
#         "data": {
#             "id": product.id,
#             "name": product.name,
#             "slug": product.slug,
#             "item_code": product.item_code,
#             "mrp": str(product.mrp),
#             "retail": str(product.retail),
#             "b2b": str(product.b2b),
#             "sku": product.sku,
#             "status": product.status,
#             "brand": str(product.brand),
#             "category": str(product.category),
#             "description": product.description,
#             "stock_quantity": product.stock_quantity,
#             "min_order_qty": product.min_order_qty,
#             "quantity_added": cart_item.quantity,
#             "images": image_list
#         }
#     }, status=200)

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_cart(request):
    user = request.user

    product_id = request.data.get("product_id")
    quantity = int(request.data.get("quantity", 1))

    if not product_id:
        return Response({
            "status": False,
            "message": "product_id is required"
        }, status=400)

    # ======================
    # GET PRODUCT
    # ======================
    product = get_object_or_404(Product, id=product_id)

    # ======================
    # GET / CREATE CART
    # ======================
    cart, _ = Cart.objects.get_or_create(user=user)

    # ======================
    # ADD / UPDATE CART ITEM
    # ======================
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={"quantity": quantity}
    )

    if not created:
        cart_item.quantity += quantity

    cart_item.save()

    # ======================
    # GET REAL CART COUNT
    # ======================
    cart_count = (
        CartItem.objects
        .filter(cart=cart)
        # .aggregate(total=Sum("quantity"))
        # .get("total")
    ) .count()

    print("Cart Count =", cart_count)

    # ======================
    # SEND WEBSOCKET EVENT
    # ======================
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        f"cart_{request.user.id}",
        {
            "type": "notify",
            "message": {
                "type": "cart_count",
                "count": cart_count
            }
        }
    )

    async_to_sync(channel_layer.group_send)(
        f"cart_{request.user.id}",
        {
            "type": "notify",
            "message": {
                "type": "cart_quantity",
                "product_id": product.id,
                "quantity": cart_item.quantity
            }
        }
    )

    print("WebSocket Event Sent")

    # ======================
    # PRODUCT IMAGES
    # ======================
    images = ProductImage.objects.filter(product=product)

    image_list = [
        request.build_absolute_uri(img.image.url)
        for img in images
        if img.image
    ]

    # ======================
    # RESPONSE
    # ======================
    return Response({
        "status": True,
        "message": "Product added to cart successfully",
        "cart_count": cart_count,
        "data": {
            "id": product.id,
            "name": product.name,
            "slug": product.slug,
            "item_code": product.item_code,
            "mrp": str(product.mrp),
            "retail": str(product.retail),
            "b2b": str(product.b2b),
            "sku": product.sku,
            "status": product.status,
            "brand": str(product.brand) if product.brand else None,
            "category": str(product.category) if product.category else None,
            "description": product.description,
            "stock_quantity": product.stock_quantity,
            "min_order_qty": product.min_order_qty,
            "quantity_added": cart_item.quantity,
            "images": image_list
        }
    }, status=200)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_cart(request):
    user = request.user

    # ======================
    # GET CART
    # ======================
    cart = Cart.objects.filter(user=user).first()

    if not cart:
        return Response({
            "status": False,
            "message": "Cart not found",
            "data": []
        }, status=404)

    # ======================
    # GET CART ITEMS
    # ======================
    cart_items = CartItem.objects.filter(cart=cart)

    data = []

    for item in cart_items:
        product = item.product

        # ======================
        # PRODUCT IMAGES
        # ======================
        images = ProductImage.objects.filter(product=product)

        image_list = [
            request.build_absolute_uri(img.image.url)
            for img in images
        ]

        # ======================
        # BUILD ITEM RESPONSE
        # ======================
        data.append({
            "cart_item_id": item.id,
            "quantity": item.quantity,

            "id": product.id,
            "name": product.name,
            "slug": product.slug,
            "item_code": product.item_code,
            "mrp": str(product.mrp),
            "retail": str(product.retail),
            "b2b": str(product.b2b),
            "sku": product.sku,
            "status": product.status,
            "brand": str(product.brand),
            "category": str(product.category),
            "description": product.description,
            "stock_quantity": product.stock_quantity,
            "min_order_qty": product.min_order_qty,

            "images": image_list
        })

    # ======================
    # RESPONSE
    # ======================
    return Response({
        "status": True,
        "message": "Cart fetched successfully",
        "total_items": len(data),
        "data": data
    }, status=200)
    
#################### delete item from cart api #############################
# @api_view(['DELETE'])
# @permission_classes([IsAuthenticated])
# def delete_cart_item(request, cart_item_id):
#     user = request.user

#     # ======================
#     # GET CART ITEM (ONLY USER'S ITEM)
#     # ======================
#     cart_item = get_object_or_404(
#         CartItem,
#         id=cart_item_id,
#         cart__user=user
#     )

#     # ======================
#     # DELETE ITEM
#     # ======================
#     cart_item.delete()

#     return Response({
#         "status": True,
#         "message": "Cart item deleted successfully"
#     }, status=200)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_cart_item(request, cart_item_id):

    user = request.user

    # ======================
    # GET CART ITEM
    # ======================
    cart_item = get_object_or_404(
        CartItem,
        id=cart_item_id,
        cart__user=user
    )

    cart = cart_item.cart

    # ======================
    # DELETE ITEM
    # ======================
    cart_item.delete()

    # ======================
    # UPDATED PRODUCT COUNT
    # ======================
    cart_count = CartItem.objects.filter(
        cart=cart
    ).count()

    # ======================
    # WEBSOCKET EVENT
    # ======================
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        f"cart_{request.user.id}",
        {
            "type": "notify",
            "message": {
                "type": "cart_count",
                "count": cart_count
            }
        }
    )

    return Response({
        "status": True,
        "message": "Cart item deleted successfully",
        "cart_count": cart_count
    }, status=200)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_cart_quantity(request):
    user = request.user

    product_id = request.data.get("product_id")
    quantity = request.data.get("quantity")

    if not product_id:
        return Response({
            "status": False,
            "message": "product_id is required"
        }, status=400)

    if not quantity:
        return Response({
            "status": False,
            "message": "quantity is required"
        }, status=400)

    cart = Cart.objects.filter(user=user).first()

    if not cart:
        return Response({
            "status": False,
            "message": "Cart not found"
        }, status=404)

    cart_item = CartItem.objects.filter(
        cart=cart,
        product_id=product_id
    ).first()

    if not cart_item:
        return Response({
            "status": False,
            "message": "Product not found in cart"
        }, status=404)

    cart_item.quantity = int(quantity)
    cart_item.save()

    return Response({
        "status": True,
        "message": "Quantity updated successfully",
        "data": {
            "product_id": cart_item.product.id,
            "product_name": cart_item.product.name,
            "quantity": cart_item.quantity
        }
    }, status=200)

######################## message api #############################

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_message(request):
    user = request.user

    message_text = request.data.get("message")

    if not message_text:
        return Response({
            "status": False,
            "message": "Message is required"
        }, status=400)

    msg = Message.objects.create(
        user=user,
        message=message_text
    )

    return Response({
        "status": True,
        "message": "Message added successfully",
        "data": {
            "id": msg.id,
            "user_id": user.id,
            "message": msg.message,
            "created_at": msg.created_at
        }
    }, status=201)

########################################### Adress api ############################################################

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def address_api(request, slug=None):
    user = request.user

    if request.method == 'GET' :
        addresses = Address.objects.filter(user=user).order_by('-is_default', '-created_at')

        data = []
        for a in addresses:
            data.append({
                "id": a.id,
                # "slug": a.slug,/
                "full_name": a.full_name,
                "mobile_number": a.mobile_number,
                "alternate_mobile_number": a.alternate_mobile_number,
                "address_line_1": a.address_line_1,
                "address_line_2": a.address_line_2,
                "city": a.city,
                "state": a.state,
                "pincode": a.pincode,
                "is_default": a.is_default,
                "created_at": a.created_at,
            })

        return JsonResponse({"status": True, "data": data})

    if request.method == 'POST':
        data = request.data

        address = Address.objects.create(
            user=user,
            full_name=data.get("full_name"),
            mobile_number=data.get("mobile_number"),
            alternate_mobile_number = data.get("alternate_mobile_number"),
            address_line_1=data.get("address_line_1"),
            address_line_2=data.get("address_line_2"),
            city=data.get("city"),
            state=data.get("state"),
            pincode=data.get("pincode"),
        )

        return JsonResponse({
            "status": True,
            "message": "Address created",
            "slug": address.slug
        })

@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def edit_address(request, address_id):
    try:
        user = request.user

        # Fetch address belonging to this user only
        try:
            address = Address.objects.get(id=address_id, user=user)
        except Address.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Address not found"},
                status=404
            )

        # Accept JSON or form-data
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        address.full_name = data.get("full_name", address.full_name)
        address.mobile_number = data.get("mobile_number", address.mobile_number)
        address.alternate_mobile_number = data.get("alternate_mobile_number", address.alternate_mobile_number)
        address.address_line_1 = data.get("address_line_1", address.address_line_1)
        address.address_line_2 = data.get("address_line_2", address.address_line_2)
        address.pincode = data.get("pincode", address.pincode)
        address.city = data.get("city", address.city)
        address.state = data.get("state", address.state)

        if "is_default" in data:
            if data["is_default"]:
                Address.objects.filter(user=user).update(is_default=False)
            address.is_default = data["is_default"]

        address.save()

        return JsonResponse(
            {"status": "success", "message": "Address updated successfully"},
            status=200
        )

    except Exception as e:
        return JsonResponse(
            {"status": "error", "message": str(e)},
            status=400
        )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_address(request, id):
    try:
        address = Address.objects.get(id=id, user=request.user)
    except Address.DoesNotExist:
        return Response({"error": "Address not found"}, status=404)

    address.delete()
    return Response({"message": "Address deleted successfully"}, status=200)
    

@api_view(["GET"])
def product_list_api(request):

    products = Product.objects.select_related(
        "brand",
        "category"
    ).filter(
        status="Publish"
    )

    # Price Filter
    price_range = request.GET.get("price")

    if price_range:
        try:
            min_price, max_price = price_range.split("-")

            products = products.filter(
                retail__gte=min_price,
                retail__lte=max_price
            )

        except ValueError:
            return JsonResponse({
                "status": False,
                "message": "Invalid price format. Use 1000-2000"
            }, status=400)

    data = []

    for p in products:

        images = ProductImage.objects.filter(product=p)

        data.append({
            "id": p.id,
            "name": p.name,
            "slug": p.slug,

            "brand": {
                "id": p.brand.id,
                "name": p.brand.name
            } if p.brand else None,

            "category": {
                "id": p.category.id,
                "name": p.category.name
            } if p.category else None,

            "retail": str(p.retail),

            "images": [
                request.build_absolute_uri(img.image.url)
                for img in images
            ]
        })

    return JsonResponse({
        "status": True,
        "total": len(data),
        "data": data
    })


def get_default_address(request, user_id):
    if request.method != "GET":
        return JsonResponse(
            {"error": "Only GET method allowed"},
            status=405
        )

    try:
        address = Address.objects.filter(
            user_id=user_id,
            is_default=True
        ).values(
            "id",
            "mobile_number",
            "address_line_1",
            "address_line_2",
            # "landmark",
            "pincode",
            "city",
            "state",
            "is_default"
        ).first()

        if not address:
            return JsonResponse(
                {"message": "No default address found"},
                status=404
            )

        return JsonResponse({
            "user_id": user_id,
            "default_address": address
        }, status=200)

    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=500
        )
    
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_default_status(request):
    address_id = request.data.get("id")
    req_default = request.data.get("is_default")

    if not address_id:
        return Response({"error": "id is required"}, status=400)

    # Convert string "True"/"False" to boolean
    is_default = str(req_default).lower() == "true"

    try:
        address = Address.objects.get(id=address_id, user=request.user)
    except Address.DoesNotExist:
        return Response({"error": "Address not found"}, status=404)

    if is_default:
        # Remove default from other addresses of this user
        Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
        # Set this address as default
        address.is_default = True
        address.save()

    return Response({
        "message": "Default address updated",
        "id": address.id,
        "is_default": address.is_default
    })


#################################################### COD ###############################################################

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def place_order(request):
    user = request.user

    address_id = request.data.get("address_id")

    if not address_id:
        return JsonResponse({
            "status": False,
            "message": "Address is required"
        }, status=400)

    address = get_object_or_404(
        Address,
        id=address_id,
        user=user
    )

    cart = get_object_or_404(Cart, user=user)

    cart_items = cart.items.all()

    if not cart_items.exists():
        return JsonResponse({
            "status": False,
            "message": "Cart is empty"
        }, status=400)

    total_amount = 0

    for item in cart_items:
        total_amount += item.product.retail * item.quantity


    order = Order.objects.create(
        user=user,
        address=address,
        total_amount=total_amount,
        payment_method="COD"
    )

    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.product.retail
        )

    cart_items.delete()

    return JsonResponse({
        "status": True,
        "message": "Order placed successfully",
        "order_id": order.id,
        "total_amount": str(order.total_amount),
        "payment_method": "COD"
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def buy_now(request):
    user = request.user

    address_id = request.data.get("address_id")
    product_id = request.data.get("product_id")
    quantity = int(request.data.get("quantity", 1))
    remarks = request.data.get("remarks")

    print(request.data)
    print("Remarks:", remarks)

    if not address_id:
        return JsonResponse({
            "status": False,
            "message": "Address is required"
        }, status=400)

    if not product_id:
        return JsonResponse({
            "status": False,
            "message": "Product is required"
        }, status=400)

    address = get_object_or_404(
        Address,
        id=address_id,
        user=user
    )

    product = get_object_or_404(
        Product,
        id=product_id,
        is_active=True
    )

    if quantity < 1:
        return JsonResponse({
            "status": False,
            "message": "Quantity must be greater than 0"
        }, status=400)

    total_amount = product.retail * quantity

    order = Order.objects.create(
        user=user,
        address=address,
        remarks = remarks,
        total_amount=total_amount,
        payment_method="COD"
    )

    OrderItem.objects.create(
        order=order,
        product=product,
        quantity=quantity,
        price=product.retail
    )

    return JsonResponse({
        "status": True,
        "message": "Order placed successfully",
        "order_id": order.id,
        "product_id": product.id,
        "quantity": quantity,
        "total_amount": str(total_amount),
        "payment_method": "COD"
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_upi_order(request):

    user = request.user

    address_id = request.data.get("address_id")
    total_amount = request.data.get("total_amount")
    payment_method = request.data.get("payment_method")
    transaction_id = request.data.get("transaction_id")
    product_id = request.data.get("product_id")
    quantity = int(request.data.get("quantity", 1))
    transaction_screenshot = request.FILES.get("transaction_screenshot")
    print(address_id)
    print(total_amount)
    print(payment_method)
    print(transaction_id)
    print(product_id)
    print(quantity)
    print(transaction_screenshot)

    if not address_id:
        return JsonResponse({
            "status": False,
            "message": "Address is required"
        }, status=400)
    
    if not product_id:
        return JsonResponse({
            "status": False,
            "message": "Product is required"
        }, status=400)

    if not total_amount:
        return JsonResponse({
            "status": False,
            "message": "Total amount is required"
        }, status=400)

    if payment_method != "UPI":
        return JsonResponse({
            "status": False,
            "message": "Payment method must be UPI"
        }, status=400)

    if not transaction_id:
        return JsonResponse({
            "status": False,
            "message": "Transaction ID is required"
        }, status=400)

    if not transaction_screenshot:
        return JsonResponse({
            "status": False,
            "message": "Transaction screenshot is required"
        }, status=400)

    address = get_object_or_404(
        Address,
        id=address_id,
        user=user
    )
    product = get_object_or_404(
        Product,
        id=product_id,
        is_active=True
    )
    if quantity < 1:
        return JsonResponse({
            "status": False,
            "message": "Quantity must be greater than 0"
        }, status=400)
    
    total_amount = product.retail * quantity

    order = Order.objects.create(
        user=user,
        address=address,
        total_amount=total_amount,
        payment_method="UPI",
        payment_status=False,  # Admin verifies later
        transaction_id=transaction_id,
        transaction_screenshot=transaction_screenshot
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        quantity=quantity,
        price=product.retail
    )

    return JsonResponse({
        "status": True,
        "message": "Order created successfully",
        "order_id": order.id,
        "payment_method": order.payment_method,
        "transaction_id": order.transaction_id,
        "order_status": order.order_status,
        "payment_status": order.payment_status,
        "total_amount": str(order.total_amount),
        "transaction_screenshot": request.build_absolute_uri(
            order.transaction_screenshot.url
        ) if order.transaction_screenshot else None
    })


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def my_upi_orders(request):

#     orders = Order.objects.filter(
#         user=request.user,
#         payment_method='UPI'
#     ).order_by('-created_at')

#     data = []

#     for order in orders:
#         data.append({
#             "order_id": order.id,
#             "transaction_id": order.transaction_id,
#             "transaction_screenshot": (
#                 request.build_absolute_uri(
#                     order.transaction_screenshot.url
#                 )
#                 if order.transaction_screenshot
#                 else None
#             ),
#             "payment_status": order.payment_status,
#             "order_status": order.order_status,
#             "total_amount": str(order.total_amount),
#             "created_at": order.created_at
#         })

#     return JsonResponse({
#         "status": True,
#         "count": len(data),
#         "data": data
#     })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_upi_orders(request):

    if request.user.role == "admin":
        orders = (
            Order.objects.filter(
                payment_method='UPI'
            )
            .select_related(
                'user',
                'address'
            )
            .prefetch_related(
                'items__product',
                'items__product__brand',
                'items__product__category',
                'items__product__images'
            )
            .order_by('-created_at')
        )
    else:
        orders = (
            Order.objects.filter(
                user=request.user,
                payment_method='UPI'
            )
            .select_related(
                'user',
                'address'
            )
            .prefetch_related(
                'items__product',
                'items__product__brand',
                'items__product__category',
                'items__product__images'
            )
            .order_by('-created_at')
        )

    data = []

    for order in orders:

        products = []

        for item in order.items.all():

            product = item.product

            product_images = []

            if product:
                for img in product.images.all():
                    if img.image:
                        product_images.append(
                            request.build_absolute_uri(img.image.url)
                        )

            products.append({
                "order_item_id": item.id,
                "quantity": item.quantity,
                "price": str(item.price),

                "product": {
                    "id": product.id if product else None,
                    "name": product.name if product else None,
                    "slug": product.slug if product else None,
                    "item_code": product.item_code if product else None,

                    "brand": (
                        product.brand.name
                        if product and product.brand else None
                    ),

                    "category": (
                        product.category.name
                        if product and product.category else None
                    ),

                    "mrp": (
                        str(product.mrp)
                        if product else None
                    ),

                    "retail": (
                        str(product.retail)
                        if product else None
                    ),

                    "b2b": (
                        str(product.b2b)
                        if product else None
                    ),

                    "sku": (
                        product.sku
                        if product else None
                    ),

                    "stock_quantity": (
                        product.stock_quantity
                        if product else None
                    ),

                    "min_order_qty": (
                        product.min_order_qty
                        if product else None
                    ),

                    # Main Product Image
                    "image": (
                        request.build_absolute_uri(product.image.url)
                        if product and product.image else None
                    ),

                    # Additional Images
                    "images": product_images,

                    "status": (
                        product.status
                        if product else None
                    ),

                    "is_active": (
                        product.is_active
                        if product else False
                    ),

                    "is_best_seller": (
                        product.is_best_seller
                        if product else False
                    ),

                    "is_available_on_order": (
                        product.is_available_on_order
                        if product else False
                    ),

                    "created_at": (
                        product.created_at
                        if product else None
                    ),

                    "updated_at": (
                        product.updated_at
                        if product else None
                    )
                }
            })

        data.append({
            "order_id": order.id,

            "user": {
                "id": order.user.id,
                "username": order.user.username,
                "email": order.user.email,
                "phone": order.user.phone,
                "business_name": order.user.business_name,
                "business_category": order.user.business_category,
                "role": order.user.role,
                "status": order.user.status,

                "image": (
                    request.build_absolute_uri(order.user.image.url)
                    if order.user.image else None
                ),

                "created_at": order.user.created_at
            },

            "address": {
                "id": order.address.id if order.address else None,
                "full_name": (
                    order.address.full_name
                    if order.address else None
                ),
                "mobile_number": (
                    order.address.mobile_number
                    if order.address else None
                ),
                "address_line_1": (
                    order.address.address_line_1
                    if order.address else None
                ),
                "address_line_2": (
                    order.address.address_line_2
                    if order.address else None
                ),
                "city": (
                    order.address.city
                    if order.address else None
                ),
                "state": (
                    order.address.state
                    if order.address else None
                ),
                "pincode": (
                    order.address.pincode
                    if order.address else None
                ),
            },

            "payment": {
                "payment_method": order.payment_method,
                "transaction_id": order.transaction_id,

                "transaction_screenshot": (
                    request.build_absolute_uri(
                        order.transaction_screenshot.url
                    )
                    if order.transaction_screenshot else None
                ),

                "payment_status": order.payment_status,
            },

            "order": {
                "total_amount": str(order.total_amount),
                "order_status": order.order_status,
                "created_at": order.created_at,
            },

            "products": products
        })

    return JsonResponse({
        "status": True,
        "count": len(data),
        "data": data
    })



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def upi_orders_by_date(request):

    if request.user.role != "admin":
        return JsonResponse({
            "status": False,
            "message": "Permission denied"
        }, status=403)

    from_date = request.GET.get("from_date")
    to_date = request.GET.get("to_date")

    orders = (
        Order.objects.filter(
            payment_method='UPI'
        )
        .select_related(
            'user',
            'address'
        )
        .prefetch_related(
            'items__product',
            'items__product__brand',
            'items__product__category',
            'items__product__images'
        )
        .order_by('-created_at')
    )

    if from_date and to_date:
        orders = orders.filter(
            created_at__date__range=[from_date, to_date]
        )

    data = []

    for order in orders:

        products = []

        for item in order.items.all():

            product = item.product

            product_images = []

            if product:
                for img in product.images.all():
                    if img.image:
                        product_images.append(
                            request.build_absolute_uri(img.image.url)
                        )

            products.append({
                "order_item_id": item.id,
                "quantity": item.quantity,
                "price": str(item.price),

                "product": {
                    "id": product.id if product else None,
                    "name": product.name if product else None,
                    "slug": product.slug if product else None,
                    "item_code": product.item_code if product else None,

                    "brand": (
                        product.brand.name
                        if product and product.brand else None
                    ),

                    "category": (
                        product.category.name
                        if product and product.category else None
                    ),

                    "mrp": (
                        str(product.mrp)
                        if product else None
                    ),

                    "retail": (
                        str(product.retail)
                        if product else None
                    ),

                    "b2b": (
                        str(product.b2b)
                        if product else None
                    ),

                    "sku": (
                        product.sku
                        if product else None
                    ),

                    "stock_quantity": (
                        product.stock_quantity
                        if product else None
                    ),

                    "min_order_qty": (
                        product.min_order_qty
                        if product else None
                    ),

                    "image": (
                        request.build_absolute_uri(product.image.url)
                        if product and product.image else None
                    ),

                    "images": product_images,

                    "status": (
                        product.status
                        if product else None
                    ),

                    "is_active": (
                        product.is_active
                        if product else False
                    ),

                    "is_best_seller": (
                        product.is_best_seller
                        if product else False
                    ),

                    "is_available_on_order": (
                        product.is_available_on_order
                        if product else False
                    ),

                    "created_at": (
                        product.created_at
                        if product else None
                    ),

                    "updated_at": (
                        product.updated_at
                        if product else None
                    )
                }
            })

        data.append({
            "order_id": order.id,

            "user": {
                "id": order.user.id,
                "username": order.user.username,
                "email": order.user.email,
                "phone": order.user.phone,
                "business_name": order.user.business_name,
                "business_category": order.user.business_category,
                "role": order.user.role,
                "status": order.user.status,

                "image": (
                    request.build_absolute_uri(order.user.image.url)
                    if order.user.image else None
                ),

                "created_at": order.user.created_at
            },

            "address": {
                "id": order.address.id if order.address else None,
                "full_name": (
                    order.address.full_name
                    if order.address else None
                ),
                "mobile_number": (
                    order.address.mobile_number
                    if order.address else None
                ),
                "address_line_1": (
                    order.address.address_line_1
                    if order.address else None
                ),
                "address_line_2": (
                    order.address.address_line_2
                    if order.address else None
                ),
                "city": (
                    order.address.city
                    if order.address else None
                ),
                "state": (
                    order.address.state
                    if order.address else None
                ),
                "pincode": (
                    order.address.pincode
                    if order.address else None
                ),
            },

            "payment": {
                "payment_method": order.payment_method,
                "transaction_id": order.transaction_id,

                "transaction_screenshot": (
                    request.build_absolute_uri(
                        order.transaction_screenshot.url
                    )
                    if order.transaction_screenshot else None
                ),

                "payment_status": order.payment_status,
            },

            "order": {
                "total_amount": str(order.total_amount),
                "order_status": order.order_status,
                "created_at": order.created_at,
            },

            "products": products
        })

    return JsonResponse({
        "status": True,
        "count": len(data),
        "data": data
    })



@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def upi_order_status_change(request, order_id):

    action = request.data.get('action')

    try:
        order = Order.objects.get(
            id=order_id,
            payment_method='UPI'
        )
    except Order.DoesNotExist:
        return Response({
            "status": False,
            "message": "UPI Order not found"
        }, status=status.HTTP_404_NOT_FOUND)

    if action == 'verified':
        order.payment_status = True
        order.order_status = 'Confirmed'
        message = "UPI order marked as verified"

    elif action == 'Rejected':
        order.payment_status = False
        order.order_status = 'Rejected'
        message = "UPI order marked as Rejected"

    # elif action == 'pending':
    #     order.payment_status = False
    #     order.order_status = 'Pending'
    #     message = "UPI order marked as pending"

    else:
        return Response({
            "status": False,
            "message": "Action must be verified or cancelled"
        }, status=status.HTTP_400_BAD_REQUEST)

    order.save()

    return Response({
        "status": True,
        "message": message,
        "order_id": order.id,
        "payment_status": order.payment_status,
        "order_status": order.order_status
    })


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def pending_upi_order_count(request):

#     pending_count = Order.objects.filter(
#         payment_method='UPI',
#         payment_status=False,
#         order_status='Pending'
#     ).count()

#     return Response({
#         "status": True,
#         "pending_upi_orders": pending_count
#     })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pending_upi_order_count(request):

    # Allow only admins
    if request.user.role != "admin":
        return Response(
            {
                "status": False,
                "message": "Permission denied"
            },
            status=403
        )

    pending_count = Order.objects.filter(
        payment_method='UPI',
        payment_status=False,
        order_status='Pending'
    ).count()

    return Response(
        {
            "status": True,
            "pending_upi_orders": pending_count
        }
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def upi_orders(request):

    status = request.GET.get('status')

    queryset = Order.objects.filter(payment_method='UPI')

    if status == 'pending':
        queryset = queryset.filter(payment_status=False)

    elif status == 'verified':
        queryset = queryset.filter(payment_status=True)

    elif status == 'cancelled':
        queryset = queryset.filter(order_status='Cancelled')

    return Response({
        "status": True,
        "count": queryset.count(),
        "data": [
            {
                "id": order.id,
                "user": order.user.username,
                "total_amount": order.total_amount,
                "payment_method": order.payment_method,
                "payment_status": order.payment_status,
                "order_status": order.order_status,
                "transaction_id": order.transaction_id
            }
            for order in queryset
        ]
    })


################################ product list without token setting ####################

from .models import Product

class PublicProductListAPIView(APIView):
    # permission_classes = [AllowAny]  # NO TOKEN

    def get(self, request):
        products = Product.objects.all().order_by('-created_at')
        results = []

        for product in products:

            # 1. Product main image
            image_url = None
            if product.image:
                image_url = request.build_absolute_uri(product.image.url)

            # 2. Extra images (ProductImage model)
            extra_images = []
            for img in product.images.all():
                if img.image:
                    extra_images.append(
                        request.build_absolute_uri(img.image.url)
                    )

            results.append({
                "id": product.id,
                "name": product.name,
                "item_code": product.item_code,
                "category": product.category.name if product.category else None,
                "brand": product.brand.name if product.brand else None,
                "description": product.description,
                "main_image": image_url,
                "images": extra_images
            })

        return Response({
            "success": True,
            "total_products": products.count(),
            "data": results
        })
    

class OrderDateFilterAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        if request.user.role != "admin":
            return Response({
                "status": False,
                "message": "Permission denied"
            }, status=403)

        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")

        orders = Order.objects.select_related(
            "user",
            "address"
        ).prefetch_related(
            "items__product"
        ).order_by("-id")

        if from_date and to_date:
            orders = orders.filter(
                created_at__date__range=[from_date, to_date]
            )

        data = []

        for order in orders:

            products = []

            for item in order.items.all():

                product = item.product

                products.append({
                    "order_item_id": item.id,
                    "quantity": item.quantity,
                    "price": str(item.price),

                    "product": {
                        "id": product.id if product else None,
                        "name": product.name if product else None,
                        "category": product.category.name if product and product.category else None,
                        "brand": product.brand.name if product and product.brand else None,
                        "mrp": str(product.mrp) if product else None,
                    }
                })

            data.append({
                "order_id": order.id,
                "order_status": order.order_status,
                "payment_method": order.payment_method,
                "payment_status": order.payment_status,
                "total_amount": str(order.total_amount),

                "user": {
                    "id": order.user.id,
                    "username": order.user.username,
                    "email": order.user.email,
                    "phone": order.user.phone,
                    "business_name": order.user.business_name,
                },

                "address": {
                    "full_name": order.address.full_name if order.address else None,
                    "mobile_number": order.address.mobile_number if order.address else None,
                    "city": order.address.city if order.address else None,
                    "state": order.address.state if order.address else None,
                    "pincode": order.address.pincode if order.address else None,
                },

                "products": products,
                "created_at": order.created_at,
            })

        return Response({
            "count": orders.count(),
            "results": data
        })


    
# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def get_cart_item_count(request):
#     user = request.user

#     try:
#         cart = Cart.objects.get(user=user)
#         item_count = cart.items.count()
#     except Cart.DoesNotExist:
#         item_count = 0

#     return JsonResponse(
#         {
#             "item_count": item_count
#         },
#         status=200
#     )

###################### Filter category,brand,price api ########################



# class OrderFilterAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):

#         category = request.GET.get('category')
#         brand = request.GET.get('brand')
#         price = request.GET.get('price')

#         orders = Order.objects.prefetch_related(
#             'items__product',
#             'items__product__brand',
#             'items__product__category'
#         ).all()

#         if category:
#             orders = orders.filter(
#                 items__product__category__name__icontains=category
#             )

#         if brand:
#             orders = orders.filter(
#                 items__product__brand__name__icontains=brand
#             )

#         if price:

#             if price == '1000-2000':
#                 orders = orders.filter(
#                     items__product__mrp__gte=1000,
#                     items__product__mrp__lte=2000
#                 )

#             elif price == '2000-4000':
#                 orders = orders.filter(
#                     items__product__mrp__gte=2000,
#                     items__product__mrp__lte=4000
#                 )

#             elif price == '4000-6000':
#                 orders = orders.filter(
#                     items__product__mrp__gte=4000,
#                     items__product__mrp__lte=6000
#                 )

#         orders = orders.distinct()

#         data = []

#         for order in orders:

#             products = []

#             for item in order.items.all():

#                 product = item.product

#                 products.append({
#                     "order_item_id": item.id,
#                     "quantity": item.quantity,
#                     "price": str(item.price),

#                     "product": {
#                         "id": product.id if product else None,
#                         "name": product.name if product else None,
#                         "category": product.category.name if product and product.category else None,
#                         "brand": product.brand.name if product and product.brand else None,
#                         "mrp": str(product.mrp) if product else None,
#                         "retail": str(product.retail) if product else None,
#                         "image": request.build_absolute_uri(product.image.url)
#                         if product and product.image else None
#                     }
#                 })

#             data.append({
#                 "order_id": order.id,
#                 "order_status": order.order_status,
#                 "payment_method": order.payment_method,
#                 "payment_status": order.payment_status,
#                 "total_amount": str(order.total_amount),
#                 "created_at": order.created_at,

#                 "customer": {
#                     "id": order.user.id,
#                     "email": order.user.email,
#                     "phone": order.user.phone,
#                     "business_name": order.user.business_name
#                 },

#                 "products": products
#             })

#         return Response({
#             "count": len(data),
#             "results": data
#         })


# class ProductFilterAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):

#         category = request.GET.get('category')
#         brand = request.GET.get('brand')
#         price = request.GET.get('price')

#         products = Product.objects.all()

#         if category:
#             products = products.filter(
#                 category__name__icontains=category
#             )

#         if brand:
#             products = products.filter(
#                 brand__name__icontains=brand
#             )

#         if price:
#             if price == '0-1000':
#                 products = products.filter(
#                     mrp__gte=0,
#                     mrp__lte=1000
#                 )

#             elif price == '1000-5000':
#                 products = products.filter(
#                     mrp__gte=1000,
#                     mrp__lte=5000
#                 )

#             elif price == '5000-10000':
#                 products = products.filter(
#                     mrp__gte=5000,
#                     mrp__lte=10000
#                 )

#             elif price == '10000-100000':
#                 products = products.filter(
#                     mrp__gte=10000,
#                     mrp__lte=100000
#                 )
            
#             elif price == '100000-infinity':
#                 products = products.filter(
#                     mrp__gte=100000
#                 )

#         data = []

#         for product in products:
#             first_image = product.images.first()

#             data.append({
#                 "id": product.id,
#                 "name": product.name,
#                 "slug": product.slug,
#                 "item_code" : product.item_code,
#                 "category": product.category.name if product.category else None,
#                 "brand": product.brand.name if product.brand else None,
#                 "mrp": product.mrp,
#                 "description": product.description,
#                 "stock_quantity": product.stock_quantity,
#                 "status": product.status,
#                 "retail": product.retail,
#                 "b2b": product.b2b,
#                 "sku": product.sku,
#                 "min_order_qty": product.min_order_qty,
#                 "image": (
#                 request.build_absolute_uri(first_image.image.url)
#                 if first_image and first_image.image
#                 else None)
#             })

#         return Response({
#             "count": products.count(),
#             "results": data
#         })


class ProductFilterAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        category = request.GET.get("category")
        brand = request.GET.get("brand")
        price = request.GET.get("price")

        display, _ = DisplaySetting.objects.get_or_create(id=1)

        products = Product.objects.filter(status="Publish")

        if category:
            products = products.filter(
                category__name__icontains=category
            )

        if brand:
            products = products.filter(
                brand__name__icontains=brand
            )

        if price:
            if price == "0-1000":
                products = products.filter(
                    mrp__gte=0,
                    mrp__lte=1000
                )

            elif price == "1000-5000":
                products = products.filter(
                    mrp__gte=1000,
                    mrp__lte=5000
                )

            elif price == "5000-10000":
                products = products.filter(
                    mrp__gte=5000,
                    mrp__lte=10000
                )

            elif price == "10000-100000":
                products = products.filter(
                    mrp__gte=10000,
                    mrp__lte=100000
                )

            elif price == "100000-infinity":
                products = products.filter(
                    mrp__gte=100000
                )

        data = []

        for product in products:

            first_image = product.images.first()

            product_data = {
                "id": product.id,
                "name": product.name,
                "slug": product.slug,
                "status": product.status,
                "min_order_qty": product.min_order_qty,

                "image": (
                    request.build_absolute_uri(first_image.image.url)
                    if first_image and first_image.image
                    else None
                ),

                "category": {
                    "id": product.category.id,
                    "name": product.category.name
                } if product.category else None,
            }

            if display.item_code:
                product_data["item_code"] = product.item_code

            if display.brand:
                product_data["brand"] = {
                    "id": product.brand.id,
                    "name": product.brand.name
                } if product.brand else None

            if display.description:
                product_data["description"] = product.description

            if display.mrp:
                product_data["mrp"] = str(product.mrp)

            if display.retail:
                product_data["retail"] = str(product.retail)

            if display.b2b:
                product_data["b2b"] = str(product.b2b)

            if display.sku:
                product_data["sku"] = product.sku

            if display.stock_quantity:
                product_data["stock_quantity"] = product.stock_quantity

            data.append(product_data)

        return Response({
            "status": True,
            "total": products.count(),
            "data": data
        })


#####################################################  DisplaySetting  ##############################################################

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_display_settings(request):

    if request.user.role != "admin":
        return Response({
            "status": False,
            "message": "Permission denied"
        }, status=403)

    settings_obj, _ = DisplaySetting.objects.get_or_create(id=1)

    settings_obj.mrp = request.data.get("mrp", settings_obj.mrp)
    settings_obj.retail = request.data.get("retail", settings_obj.retail)
    settings_obj.b2b = request.data.get("b2b", settings_obj.b2b)
    settings_obj.description = request.data.get("description", settings_obj.description)
    settings_obj.brand = request.data.get("brand", settings_obj.brand)
    settings_obj.item_code = request.data.get("item_code", settings_obj.item_code)
    settings_obj.sku = request.data.get("sku", settings_obj.sku)
    settings_obj.stock_quantity = request.data.get("stock_quantity", settings_obj.stock_quantity)

    settings_obj.save()

    return Response({
        "status": True,
        "message": "Display settings updated"
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_display_settings(request):

    settings_obj, _ = DisplaySetting.objects.get_or_create(id=1)

    return Response({
        "mrp": settings_obj.mrp,
        "retail": settings_obj.retail,
        "b2b": settings_obj.b2b,
        "description": settings_obj.description,
        "brand": settings_obj.brand,
        "item_code": settings_obj.item_code,
        "sku": settings_obj.sku,
        "stock_quantity": settings_obj.stock_quantity,
    })


# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def get_last_order_details(request):
#     user = request.user

#     order = (
#         Order.objects.filter(user=user)
#         .order_by("-created_at")
#         .first()
#     )

#     if not order:
#         return JsonResponse({
#             "status": False,
#             "message": "No orders found."
#         }, status=404)

#     return JsonResponse({
#         "status": True,
#         "data": {
#             "company_name": user.business_name,
#             "email": user.email,
#             "mobile": user.phone,
#             "remarks": order.remarks,
#             "order_id": order.id,
#             "created_at": order.created_at,
#         }
#     })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_last_order_details(request):

    orders = (
        Order.objects
        .exclude(remarks__isnull=True)
        .exclude(remarks="")
        .order_by("-created_at")
    )

    if not orders.exists():
        return JsonResponse({
            "status": False,
            "message": "No orders found."
        }, status=404)

    data = []

    for order in orders:
        data.append({
            "company_name": order.user.business_name,
            "email": order.user.email,
            "mobile": order.user.phone,
            "remarks": order.remarks,
            "order_id": order.id,
            "created_at": order.created_at,
        })

    return JsonResponse({
        "status": True,
        "count": len(data),
        "data": data
    })


# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def get_cart_item_count(request):
#     user = request.user

#     try:
#         cart = Cart.objects.get(user=user)
#         item_count = cart.items.count()
#     except Cart.DoesNotExist:
#         item_count = 0

#     return JsonResponse(
#         {
#             "item_count": item_count
#         },
#         status=200
#     )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_cart_item_count(request):

    user = request.user
    product_id = request.GET.get("product_id")

    if not product_id:
        return JsonResponse(
            {
                "status": False,
                "message": "product_id is required"
            },
            status=400
        )

    try:
        cart = Cart.objects.get(user=user)

        cart_item = CartItem.objects.filter(
            cart=cart,
            product_id=product_id
        ).first()

        quantity = cart_item.quantity if cart_item else 0

    except Cart.DoesNotExist:
        quantity = 0

    return JsonResponse(
        {
            "status": True,
            "product_id": int(product_id),
            "quantity": quantity
        },
        status=200
    )