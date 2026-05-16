from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model

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