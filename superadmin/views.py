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



# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_all_users(request):
#     try:
#         # Logged in user
#         user = request.user

#         # Check admin role
#         if user.role != 'admin':
#             return Response({
#                 'message': 'Only admin can access this API'
#             }, status=403)

#         # Pagination params
#         page = int(request.GET.get('page', 1))
#         limit = int(request.GET.get('limit', 10))

#         # Get all users
#         users = User.objects.filter(
#             role='user'
#         ).order_by('-created_at')

#         # Pagination
#         paginator = Paginator(users, limit)
#         current_page = paginator.get_page(page)

#         data = []

#         for user_obj in current_page:

#             image_url = (
#                 request.build_absolute_uri(user_obj.image.url)
#                 if user_obj.image else None
#             )

#             data.append({
#                 'id': user_obj.id,
#                 'username': user_obj.username,
#                 'email': user_obj.email,
#                 'mobile': user_obj.phone,
#                 'business_name': user_obj.business_name,
#                 'business_category': user_obj.business_category,
#                 'role': user_obj.role,
#                 'status': user_obj.status,
#                 'is_active': user_obj.is_active,
#                 'image': image_url,
#                 'created_at': user_obj.created_at
#             })

#         return Response({
#             'message': 'User data fetched successfully',

#             'pagination': {
#                 'current_page': page,
#                 'total_pages': paginator.num_pages,
#                 'total_users': paginator.count,
#                 'has_next': current_page.has_next(),
#                 'has_previous': current_page.has_previous(),
#                 'limit': limit
#             },

#             'data': data

#         }, status=200)

#     except Exception as e:
#         return Response({
#             'message': 'Something went wrong',
#             'error': str(e)
#         }, status=500)


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
    


# @api_view(['PUT'])
# @permission_classes([IsAuthenticated])
# def update_user_status(request, user_id):
#     try:
#         # Logged in user
#         admin_user = request.user

#         # Check admin role
#         if admin_user.role != 'admin':
#             return Response({
#                 'message': 'Only admin can update status'
#             }, status=403)

#         # Get user
#         try:
#             user = User.objects.get(id=user_id, role='user')

#         except User.DoesNotExist:
#             return Response({
#                 'message': 'User not found'
#             }, status=404)

#         # Get status
#         status_value = request.data.get('status')

#         # Validate status
#         if status_value not in ['approved', 'rejected']:
#             return Response({
#                 'message': 'Status must be approved or rejected'
#             }, status=400)

#         # Update status
#         user.status = status_value

#         # Handle is_active
#         if status_value == 'approved':
#             user.is_active = True

#         elif status_value == 'rejected':
#             user.is_active = False

#         user.save()

#         return Response({
#             'message': f'User status updated to {status_value}',
#             'data': {
#                 'user_id': user.id,
#                 'username': user.username,
#                 'email': user.email,
#                 'status': user.status,
#                 'is_active': user.is_active
#             }
#         }, status=200)

#     except Exception as e:
#         return Response({
#             'message': 'Something went wrong',
#             'error': str(e)
#         }, status=500)


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
