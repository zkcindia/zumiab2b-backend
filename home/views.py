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
    


# @csrf_exempt
# def signup(request):
#     if request.method != 'POST':
#         return JsonResponse({'message': 'Invalid request method'}, status=405)

#     try:
#         jsondata = JSONParser().parse(request)
#         username = jsondata.get('username')
#         phone = jsondata.get('mobile')
#         email = jsondata.get('email')

#         if not email:
#             return JsonResponse({'message': 'Email is required'}, status=400)

#         # Check if user already exists
#         if User.objects.filter(email=email).exists():
#             return JsonResponse({'message': 'Email already in use'}, status=400)

#         # Create user
#         csrf_token = csrf.get_token(request)

#         user = User.objects.create(
#             username=username,
#             phone=phone,
#             email=email,
#             otp_code=None
#         )

#         # Save CSRF token on user if needed
#         user.csrf_token = csrf_token if hasattr(user, 'csrf_token') else None
#         user.save()

#         # Full image URL
#         image_url = request.build_absolute_uri(user.image.url) if user.image else None

#         return JsonResponse({
#             'message': 'Data saved successfully',
#             'email': user.email,
#             'mobile':user.phone,
#             'user_id':user.id,
#             'csrf_token': csrf_token,
#             'image': image_url,
#             'permission': ['User']
#         }, status=201)

#     except Exception as e:
#         return JsonResponse({'message': 'Something went wrong', 'error': str(e)}, status=500)


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


# @csrf_exempt
# def login(request):
#     if request.method == 'POST':
#         jsondata = JSONParser().parse(request)
#         email = jsondata.get('email')

#         if not email:
#             return JsonResponse({'message': 'Email is required'}, status=400)

#         user = None

#         # 1. Try Myuser
#         try:
#             user = User.objects.get(email=email)
#         except User.DoesNotExist:
#             return JsonResponse({'message': 'Email not exists !!'}, status=400)

#         # Generate and save OTP
#         otp_code = generate_otp()
#         print("Generated OTP:", otp_code)

#         if hasattr(user, 'otp_code'):
#             user.otp_code = otp_code
#         elif hasattr(user, 'otp'):
#             user.otp = otp_code
#             user.otp_created_at = timezone.now()
#         else:
#             return JsonResponse({'message': 'Unable to assign OTP'}, status=500)

#         user.save()

#         # Send OTP
#         send_forget_password_mail(email, otp_code)

#         return JsonResponse({'message': 'Email sent'}, status=200)

#     else:
#         return JsonResponse({'message': 'Invalid request method'}, status=400)

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
#########################Catgory API#########################

from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework import status
from .models import Category

import json
@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def category(request, slug=None):

    # =========================
    # GET ALL
    # =========================
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

        # GET SINGLE
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


    # =========================
    # CREATE
    # =========================
    if request.method == 'POST':
        obj = Category.objects.create(
            name=request.data.get('name')
        )

        return JsonResponse({
            "message": "Category created successfully",
            "id": obj.id
        }, status=201)


    # =========================
    # UPDATE
    # =========================
    if request.method == 'PUT':
        try:
            obj = Category.objects.get(slug=slug)
            obj.name = request.data.get('name')
            obj.save()

            return JsonResponse({"message": "updated successfully"})

        except Category.DoesNotExist:
            return JsonResponse({"error": "not found"}, status=404)


    # =========================
    # DELETE (FIXED)
    # =========================
    if request.method == 'DELETE':
        try:
            obj = Category.objects.get(slug=slug)   # ✅ FIXED HERE
            obj.delete()

            return JsonResponse({"message": "deleted successfully"}, status=200)

        except Category.DoesNotExist:
            return JsonResponse({"error": "not found"}, status=404)
        
        ########################################## catogary status changes#############################
   

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
    
################################Catigory Publicer Unpublish status changes############################
@api_view(['GET'])
def publish_category(request, slug=None):

    # =========================
    # GET ALL PUBLISHED CATEGORY
    # =========================
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

    # =========================
    # GET SINGLE PUBLISHED CATEGORY
    # =========================
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
        
        #############################Brand Api#############################
  
from .models import Brand


@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def brand(request, slug=None):

    # =========================
    # GET ALL
    # =========================
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

        # =========================
        # GET SINGLE
        # =========================
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

    # =========================
    # CREATE
    # =========================
    if request.method == 'POST':
        obj = Brand.objects.create(
            name=request.data.get('name')
        )

        return JsonResponse({
            "message": "Brand created successfully",
            "id": obj.id
        }, status=201)

    # =========================
    # UPDATE
    # =========================
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

    # =========================
    # DELETE
    # =========================
    if request.method == 'DELETE':
        try:
            obj = Brand.objects.get(slug=slug)
            obj.delete()

            return JsonResponse({
                "message": "deleted successfully"
            }, status=200)

        except Brand.DoesNotExist:
            return JsonResponse({"error": "not found"}, status=404)    
############################status Brand changes #############################
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
######################## Brand Publices get api #############################
@api_view(['GET'])
def publish_brand(request, slug=None):

    # =========================
    # GET ALL PUBLISHED BRAND
    # =========================
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

    # =========================
    # GET SINGLE PUBLISHED BRAND
    # =========================
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
        
        
#######################3 Product API #############################

from .models import Product
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator, EmptyPage
from django.utils.text import slugify
from .models import Product, ProductImage
from django.db.models import Case, When, Value, IntegerField

@csrf_exempt

def product_api(request, slug=None):

    # =========================
    # GET (LIST + SINGLE)
    # =========================
    if request.method == "GET":

        # -------- SINGLE PRODUCT --------
        if slug:
            try:
                p = Product.objects.get(slug=slug)
                images = ProductImage.objects.filter(product=p)

                return JsonResponse({
                    # "id": p.id,
                    "name": p.name or "",
                    "slug": p.slug or "", 
                    "item_code": p.item_code or "",
                    "brand": p.brand or "",
                    "description": p.description or "",
                    "category": p.category or "",
                    "status": p.status or "",

                    "mrp": str(p.mrp or 0),
                    "retail": str(p.retail or 0),
                    "b2b": str(p.b2b or 0),

                    "sku": p.sku or "",
                    "stock_quantity": p.stock_quantity or 0,
                    "min_order_qty": p.min_order_qty or 0,

                    "is_best_seller": bool(p.is_best_seller),
                    "is_available_on_order": bool(p.is_available_on_order),
                    "is_active": bool(p.is_active),

                    "images": [
                        request.build_absolute_uri(i.image.url)
                        for i in images
                    ]
                })

            except Product.DoesNotExist:
                return JsonResponse({
                    "status": False,
                    "message": "Product not found"
                }, status=404)

        # -------- LIST PRODUCTS --------
        page = int(request.GET.get("page", 1))
        limit = int(request.GET.get("limit", 5))

        # products = Product.objects.all().order_by("-id")
        products = Product.objects.annotate(
        status_order=Case(
            When(status='Publish', then=Value(1)),
            When(status='Unpublish', then=Value(2)),
            default=Value(3),
            output_field=IntegerField()
        )
    ).order_by('status_order', '-id')

        paginator = Paginator(products, limit)

        try:
            page_data = paginator.page(page)

        except EmptyPage:
            return JsonResponse({
                "status": False,
                "message": "No data found"
            }, status=404)

        result = []

        for p in page_data:

            images = ProductImage.objects.filter(product=p)

            result.append({
                # "id": p.id,
                "name": p.name or "",
                "slug": p.slug or "",
                "item_code": p.item_code or "",
                "brand": p.brand or "",
                "description": p.description or "",
                "category": p.category or "",
                "status": p.status or "",
                "mrp": str(p.mrp or 0),
                "retail": str(p.retail or 0),
                "b2b": str(p.b2b or 0),
            
                "sku": p.sku or "",
                "stock_quantity": p.stock_quantity or 0,
                "min_order_qty": p.min_order_qty or 0,

                "images": [
                    request.build_absolute_uri(i.image.url)
                    for i in images
                ]
            })

        return JsonResponse({
            "status": True,
            "total": paginator.count,
            "page": page,
            "limit": limit,
            "data": result
        })

    # =========================
    # POST (CREATE)
    # =========================
    if request.method == "POST":

            name = request.POST.get("name")

            product = Product.objects.create(
                name=name,
                slug=slugify(name),   # ✅ SLUG ADDED

                item_code=request.POST.get("item_code"),
                brand=request.POST.get("brand"),
                description=request.POST.get("description"),
                category=request.POST.get("category"),
                status=request.POST.get("status") or "publish",    
                mrp=request.POST.get("mrp") or 0,
                retail=request.POST.get("retail") or 0,
                b2b=request.POST.get("b2b") or 0,

                sku=request.POST.get("sku"),
                stock_quantity=request.POST.get("stock_quantity") or 0,
                min_order_qty=request.POST.get("min_order_qty") or 1,

                is_best_seller=request.POST.get("is_best_seller") == "true",
                is_available_on_order=request.POST.get("is_available_on_order") == "true",
                is_active=request.POST.get("is_active") != "false",
            )


            images = request.FILES.getlist("images")

            image_list = []

            for img in images:
                obj = ProductImage.objects.create(
                    product=product,
                    image=img
                )
                image_list.append(request.build_absolute_uri(obj.image.url))

            return JsonResponse({
                "status": True,
                "message": "Product created successfully",

                # "id": product.id,
                "name": product.name or "",
                "slug": product.slug or "",   # ✅ RETURN SLUG

                "item_code": product.item_code or "",
                "brand": product.brand or "",
                "category": product.category or "",
                "description": product.description or "",
                "mrp": str(product.mrp or 0),
                "status": product.status or "",
                "retail": str(product.retail or 0),
                "b2b": str(product.b2b or 0),
                "sku": product.sku or "",
                "stock_quantity": product.stock_quantity or 0,
                "min_order_qty": product.min_order_qty or 0,
    # ✅ RETURN DESCRIPTION
                "images": image_list
            })

    # =========================
    # PUT (UPDATE)
    # =========================
    if request.method == "PUT":

        if not pk:
            return JsonResponse({"status": False, "message": "Product ID required"}, status=400)

        try:
            product = Product.objects.get(id=pk)

            data = json.loads(request.body or "{}")

            product.name = data.get("name", product.name)
            product.item_code = data.get("item_code", product.item_code)
            product.brand = data.get("brand", product.brand)
            product.description = data.get("description", product.description)  # ✅ DESCRIPTION
            product.category = data.get("category", product.category)

            product.mrp = data.get("mrp", product.mrp)
            product.retail = data.get("retail", product.retail)
            product.b2b = data.get("b2b", product.b2b)

            product.sku = data.get("sku", product.sku)
            product.stock_quantity = data.get("stock_quantity", product.stock_quantity)
            product.min_order_qty = data.get("min_order_qty", product.min_order_qty)

            product.is_best_seller = data.get("is_best_seller", product.is_best_seller)
            product.is_available_on_order = data.get("is_available_on_order", product.is_available_on_order)
            product.is_active = data.get("is_active", product.is_active)

            product.save()

            # ADD NEW IMAGES
            new_images = request.FILES.getlist("images")

            for img in new_images:
                ProductImage.objects.create(
                    product=product,
                    image=img
                )

            images = ProductImage.objects.filter(product=product)

            return JsonResponse({
                "status": True,
                "message": "Product updated successfully",
                "id": product.id,
                "name": product.name or "",
                "item_code": product.item_code or "",
                "brand": product.brand or "",
                "description": product.description or "",
                "category": product.category or "",

                "mrp": str(product.mrp or 0),
                "retail": str(product.retail or 0),
                "b2b": str(product.b2b or 0),

                "sku": product.sku or "",
                "stock_quantity": product.stock_quantity or 0,
                "min_order_qty": product.min_order_qty or 0,
                "images": [
                    request.build_absolute_uri(i.image.url)
                    for i in images
                ]
            })

        except Product.DoesNotExist:
            return JsonResponse({"status": False, "message": "Product not found"}, status=404)

    # =========================
    # DELETE
    # =========================
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
###################################product status changes##################################
# @csrf_exempt
# def product_status_api(request, slug):

#     if request.method == "POST":
#         try:
#             p = Product.objects.get(slug=slug)

#             new_status = request.POST.get("status")  # Publish / Unpublish

#             if new_status not in ["Publish", "Unpublish"]:
#                 return JsonResponse({
#                     "status": False,
#                     "message": "Invalid status"
#                 }, status=400)

#             p.status = new_status
#             p.save()

#             return JsonResponse({
#                 "status": True,
#                 "message": "Status updated successfully",
#                 "product": {
#                     "slug": p.slug,
#                     "status": p.status
#                 }
#             })

#         except Product.DoesNotExist:
#             return JsonResponse({
#                 "status": False,
#                 "message": "Product not found"
#             }, status=404)
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

@api_view(['GET'])
def product_list_api(request):

    products = Product.objects.filter(status="Publish").order_by('-id')

    data = []
    for p in products:
        
         # GET MULTIPLE IMAGES
        product_images = ProductImage.objects.filter(product=p)

        image_list = []

        for img in product_images:
            if img.image:
                image_list.append(
                    request.build_absolute_uri(img.image.url)
                )
        data.append({
            "id": p.id,
            "name": p.name,
            "slug": p.slug,
            "item_code": p.item_code,
            "mrp": p.mrp,
            "retail": p.retail,
            "b2b": p.b2b,

            "sku": p.sku,   
            "status": p.status,
            "brand": p.brand,
            "category": p.category,
            "description": p.description,
            "stock_quantity": p.stock_quantity,
            
            "min_order_qty": p.min_order_qty,
            "images": image_list

            
        })

    return JsonResponse({
        "status": True,
        "total": len(data),
        "data": data
    })
    ######################## Category Datils Api #############################
#     from django.http import JsonResponse
# from .models import Category

# # =========================
# # FILTER CATEGORY API
# # =========================
# def category_list_api(request):

#     # QUERY PARAM
#     name = request.GET.get("name")

#     categories = Category.objects.all().order_by('-id')

#     # FILTER BY CATEGORY NAME
#     if name:
#         categories = categories.filter(name__icontains=name)

#     data = []

#     for c in categories:

#         data.append({
#             "id": c.id,
#             "name": c.name or "",
#             "slug": c.slug or "",
#             "status": c.status or "",
#             "created_at": c.created_at,
#         })

#     return JsonResponse({
#         "status": True,
#         "total": len(data),
#         "data": data
#     })
 ######################################Export api######################################
from io import StringIO

import csv
from django.http import StreamingHttpResponse, HttpResponse
from django.db import connection
import logging

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

