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
from home. views import *
import json, random
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.paginator import Paginator
from superadmin.helpers import (
    send_approved_mail,
    send_rejected_mail
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_users(request):

    try:

        # Logged in user
        user = request.user

        # Check admin role
        if user.role != 'admin':

            return Response({
                'message': 'Only admin can access this API'
            }, status=403)

        # ================= PAGINATION =================

        page = int(request.GET.get('page', 1))

        limit = int(request.GET.get('limit', 10))

        # ================= FILTER =================

        status_filter = request.GET.get('status')

        # Base queryset
        users = User.objects.filter(
            role='user'
        ).order_by('-created_at')

        # Apply status filter
        if status_filter:

            users = users.filter(
                status=status_filter
            )

        # ================= PAGINATION =================

        paginator = Paginator(users, limit)

        current_page = paginator.get_page(page)

        data = []

        for user_obj in current_page:

            image_url = (
                request.build_absolute_uri(user_obj.image.url)
                if user_obj.image else None
            )

            data.append({

                'id': user_obj.id,

                'username': user_obj.username,

                'email': user_obj.email,

                'mobile': user_obj.phone,

                'business_name': user_obj.business_name,

                'business_category': user_obj.business_category,

                'role': user_obj.role,

                'status': user_obj.status,

                'is_active': user_obj.is_active,

                'image': image_url,

                'created_at': user_obj.created_at

            })

        return Response({

            'message': 'User data fetched successfully',

            'pagination': {

                'current_page': page,

                'total_pages': paginator.num_pages,

                'total_users': paginator.count,

                'has_next': current_page.has_next(),

                'has_previous': current_page.has_previous(),

                'limit': limit

            },

            'filters': {

                'status': status_filter

            },

            'data': data

        }, status=200)

    except Exception as e:

        return Response({
            'message': 'Something went wrong',
            'error': str(e)
        }, status=500)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user_status(request, user_id):

    try:

        # Logged in user
        admin_user = request.user

        # Check admin role
        if admin_user.role != 'admin':
            return Response({
                'message': 'Only admin can update status'
            }, status=403)

        # Get requested user
        try:
            user = User.objects.get(
                id=user_id,
                role='user'
            )

        except User.DoesNotExist:
            return Response({
                'message': 'User not found'
            }, status=404)

        # Get status
        status_value = request.data.get('status')

        # Validate status
        if status_value not in ['approved', 'rejected']:

            return Response({
                'message': 'Status must be approved or rejected'
            }, status=400)

        # Frontend login URL
        login_url = "http://192.168.29.78:8000/login"

        # ================= APPROVED =================

        if status_value == 'approved':

            user.status = 'approved'

            user.is_active = True

            user.save()

            # Send approval mail
            send_approved_mail(
                user.email,
                user.username,
                login_url
            )

            return Response({

                'message': 'User approved successfully',

                'data': {
                    'user_id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'status': user.status,
                    'is_active': user.is_active
                }

            }, status=200)

        # ================= REJECTED =================

        if status_value == 'rejected':

            # Send rejection mail
            send_rejected_mail(
                user.email,
                user.username
            )

            # Delete user
            user.delete()

            return Response({
                'message': 'User rejected and deleted successfully'
            }, status=200)

    except Exception as e:

        return Response({
            'message': 'Something went wrong',
            'error': str(e)
        }, status=500)


################################################################################################################

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

######################################## Percentage order status api ########################################################################################


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

############################################################### ALL ORDER ###################################################################
# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def order_list(request):

#     orders = Order.objects.all().prefetch_related(
#         'items__product',
#         'items__product__images'
#     ).order_by('-id')

#     data = []

#     for order in orders:

#         products = []

#         for item in order.items.all():

#             product = item.product

#             product_images = []

#             if product:
#                 for img in product.images.all():
#                     product_images.append(
#                         request.build_absolute_uri(img.image.url)
#                     )

#             products.append({
#                 "order_item_id": item.id,
#                 "quantity": item.quantity,
#                 "price": str(item.price),

#                 "product": {
#                     "id": product.id if product else None,
#                     "name": product.name if product else None,
#                     "item_code": product.item_code if product else None,
#                     "retail": str(product.retail) if product else None,

#                     "image": (
#                         request.build_absolute_uri(product.image.url)
#                         if product and product.image else None
#                     ),

#                     "images": product_images
#                 }
#             })

#         data.append({
#             "order_id": order.id,
#             "status": order.order_status,
#             "transaction_id": order.transaction_id,
#             "customer_name": order.address.full_name if order.address else "",
#             "business_name": order.user.business_name,
#             "email": order.user.email,
#             "phone": order.user.phone,
#             "total_amount": str(order.total_amount),
#             "payment_method": order.payment_method,

#             "address": {
#                 "full_name": order.address.full_name if order.address else "",
#                 "mobile_number": order.address.mobile_number if order.address else "",
#                 "address_line_1": order.address.address_line_1 if order.address else "",
#                 "address_line_2": order.address.address_line_2 if order.address else "",
#                 "city": order.address.city if order.address else "",
#                 "state": order.address.state if order.address else "",
#                 "pincode": order.address.pincode if order.address else "",
#             },

#             "products": products,

#             "created_at": order.created_at,
#         })

#     return JsonResponse({
#         "total_orders": orders.count(),
#         "data": data
#     })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_list(request):

    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 10))

    orders = (
        Order.objects
        .all()
        .prefetch_related(
            'items__product',
            'items__product__images'
        )
        .order_by('-id')
    )

    paginator = Paginator(orders, page_size)

    current_page = paginator.get_page(page)

    data = []

    for order in current_page:

        products = []

        for item in order.items.all():

            product = item.product

            product_images = []

            if product:
                for img in product.images.all():

                    product_images.append(
                        request.build_absolute_uri(
                            img.image.url
                        )
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
                        request.build_absolute_uri(
                            product.image.url
                        )
                        if product and product.image
                        else None
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
                "alternate_mobile_number": order.address.alternate_mobile_number if order.address else "",
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
        "status": True,
        "total_orders": paginator.count,
        "total_pages": paginator.num_pages,
        "current_page": page,
        "page_size": page_size,
        "has_next": current_page.has_next(),
        "has_previous": current_page.has_previous(),
        "data": data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_details(request, order_id):

    # Allow only admin users
    if request.user.role != "admin":
        return JsonResponse(
            {
                "status": False,
                "message": "Permission denied"
            },
            status=403
        )

    order = get_object_or_404(
        Order.objects.prefetch_related(
            'items__product',
            'items__product__images'
        ),
        id=order_id
    )

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

    data = {
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
    }

    return JsonResponse(
        {
            "status": True,
            "data": data
        }
    )


########################################################################################################################################


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



################################################################ Manager #################################################################

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def manager_product_api(request, slug=None):

    # Manager only
    if request.user.role != "manager":
        return JsonResponse(
            {
                "status": False,
                "message": "Only manager can access this API"
            },
            status=403
        )


    # ================= GET =================
    if request.method == "GET":

        # Single product
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
                        "images": [
                            request.build_absolute_uri(img.image.url)
                            for img in images
                        ]
                    }
                })

            except Product.DoesNotExist:
                return JsonResponse(
                    {
                        "status": False,
                        "message": "Product not found"
                    },
                    status=404
                )


        # Product list
        products = Product.objects.select_related(
            "brand",
            "category"
        ).all()


        data = []

        for product in products:

            data.append({
                "id": product.id,
                "name": product.name,
                "slug": product.slug,
            })


        return JsonResponse({
            "status": True,
            "data": data
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
    

##################################################### QR code #######################################################################

import qrcode 
from io import BytesIO 
from django.http import HttpResponse 

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def generate_upi_qr(request): 
    amount = request.GET.get("amount", "0") 
    upi_id = "eazypay.571345224@icici" 
    merchant_name = "M/S.LIGHT HUB" 
    upi_link = ( f"upi://pay?" 
                f"pa={upi_id}" 
                f"&pn={merchant_name}" 
                f"&am={amount}" 
                f"&cu=INR" ) 
    qr = qrcode.make(upi_link) 
    buffer = BytesIO() 
    qr.save(buffer, format="PNG") 
    buffer.seek(0)
    
    return HttpResponse( 
        buffer.getvalue(), 
        content_type="image/png", 
        )