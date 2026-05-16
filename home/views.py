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
        return JsonResponse({'message': 'Invalid request method'}, status=405)

    try:
        jsondata = JSONParser().parse(request)
        username = jsondata.get('username')
        phone = jsondata.get('mobile')
        email = jsondata.get('email')

        if not email:
            return JsonResponse({'message': 'Email is required'}, status=400)

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            return JsonResponse({'message': 'Email already in use'}, status=400)

        # Create user
        csrf_token = csrf.get_token(request)

        user = User.objects.create(
            username=username,
            phone=phone,
            email=email,
            otp_code=None
        )

        # Save CSRF token on user if needed
        user.csrf_token = csrf_token if hasattr(user, 'csrf_token') else None
        user.save()

        # Full image URL
        image_url = request.build_absolute_uri(user.image.url) if user.image else None

        return JsonResponse({
            'message': 'Data saved successfully',
            'email': user.email,
            'mobile':user.phone,
            'user_id':user.id,
            'csrf_token': csrf_token,
            'image': image_url,
            'permission': ['User']
        }, status=201)

    except Exception as e:
        return JsonResponse({'message': 'Something went wrong', 'error': str(e)}, status=500)


@csrf_exempt
def login(request):
    if request.method == 'POST':
        jsondata = JSONParser().parse(request)
        email = jsondata.get('email')

        if not email:
            return JsonResponse({'message': 'Email is required'}, status=400)

        user = None

        # 1. Try Myuser
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({'message': 'Email not exists !!'}, status=400)

        # Generate and save OTP
        otp_code = generate_otp()
        print("Generated OTP:", otp_code)

        if hasattr(user, 'otp_code'):
            user.otp_code = otp_code
        elif hasattr(user, 'otp'):
            user.otp = otp_code
            user.otp_created_at = timezone.now()
        else:
            return JsonResponse({'message': 'Unable to assign OTP'}, status=500)

        user.save()

        # Send OTP
        send_forget_password_mail(email, otp_code)

        return JsonResponse({'message': 'Email sent'}, status=200)

    else:
        return JsonResponse({'message': 'Invalid request method'}, status=400)

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

        # Fetch all addresses of this user
        user_addresses = []
        for addr in user.addresses.all():
            user_addresses.append({
                "id": addr.id,
                "phone": addr.phone,
                "address_line1": addr.address_line1,
                "address_line2": addr.address_line2,
                "landmark": addr.landmark,
                "pincode": addr.pincode,
                "city": addr.city,
                "state": addr.state,
                "is_default": addr.is_default
            })

        # Final response
        return JsonResponse({
            'message': 'Login successful',
            'email': user.email,
            'image': user.image.url if user.image else None,
            'permission': user.role,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'addresses': user_addresses
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