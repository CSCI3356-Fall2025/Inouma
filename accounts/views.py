from django.shortcuts import render, redirect
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.contrib.auth.hashers import check_password
import re

from .models import User
from .serializers import UserSerializer
from Inouma.settings import auth
from decouple import config
import requests


class AuthCreateNewUserView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        operation_summary="Create a new user",
        operation_description="Create a new user by providing the required fields.",
        tags=["User Management"],
        request_body=UserSerializer,
        responses={201: UserSerializer(many=False), 400: "User creation failed."},
    )
    def post(self, request):
        data = request.data
        email = data.get('email')
        password = data.get('password')
        first_name = data.get('first_name')
        last_name = data.get('last_name')

        # Check required fields
        if not all([email, password, first_name, last_name]):
            return Response(
                {"status": "failed", "message": "All fields are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate email format
        if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return Response(
                {"status": "failed", "message": "Enter a valid email address."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate password length
        if len(password) < 8:
            return Response(
                {"status": "failed", "message": "Password must be at least 8 characters long."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate password complexity
        password_pattern = r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()_+{}\[\]:;<>,.?~\\-]).{8,}$"
        if not re.match(password_pattern, password):
            return Response(
                {
                    "status": "failed",
                    "message": "Password must contain at least one uppercase, one lowercase, one digit, and one special character."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Create user on Firebase
            user = auth.create_user_with_email_and_password(email, password)
            uid = user['localId']

            # Prepare Django user data
            data["firebase_uid"] = uid
            data["is_active"] = True

            # Save user in Django database
            serializer = UserSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {
                        "status": "success",
                        "message": "User created successfully.",
                        "data": serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                auth.delete_user_account(user['idToken'])
                return Response(
                    {
                        "status": "failed",
                        "message": "User signup failed.",
                        "data": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception:
            return Response(
                {"status": "failed", "message": "User with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )



class AuthLoginExistingUserView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        operation_summary="Login an existing user",
        operation_description="Login an existing user by providing email and password.",
        tags=["User Management"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email of the user'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password of the user'),
            },
        ),
        responses={200: UserSerializer(many=False), 404: "User does not exist."},
    )
    def post(self, request: Request):
        data = request.data
        email = data.get('email')
        password = data.get('password')

        # Authenticate via Firebase
        try:
            user = auth.sign_in_with_email_and_password(email, password)
        except Exception:
            return Response(
                {"status": "failed", "message": "Invalid email or password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            existing_user = User.objects.get(email=email)

            # Update password if changed
            if not check_password(password, existing_user.password):
                existing_user.set_password(password)
                existing_user.save()

            serializer = UserSerializer(existing_user)
            extra_data = {
                "firebase_id": user['localId'],
                "firebase_access_token": user['idToken'],
                "firebase_refresh_token": user['refreshToken'],
                "firebase_expires_in": user['expiresIn'],
                "firebase_kind": user['kind'],
                "user_data": serializer.data,
            }

            return Response(
                {"status": "success", "message": "User logged in successfully.", "data": extra_data},
                status=status.HTTP_200_OK,
            )

        except User.DoesNotExist:
            auth.delete_user_account(user['idToken'])
            return Response(
                {"status": "failed", "message": "User does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )


class AuthGoogleOAuthCallbackView(APIView):

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        code = request.GET.get('code')
        if not code:
            return Response({"status": "failed", "message": "Missing authorization code."}, status=status.HTTP_400_BAD_REQUEST)

        # Exchange the authorization code for tokens
        token_url = 'https://oauth2.googleapis.com/token'
        client_id = config('GOOGLE_CLIENT_ID', default=None)
        client_secret = config('GOOGLE_CLIENT_SECRET', default=None)
        # Redirect URI must match the one registered exactly
        redirect_uri = config('GOOGLE_REDIRECT_URI', default='http://localhost:8000/auth/oauth2callback')

        data = {
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }

        try:
            token_resp = requests.post(token_url, data=data, timeout=10)
            token_resp.raise_for_status()
        except Exception as e:
            return Response({"status": "failed", "message": f"Token exchange failed: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        token_json = token_resp.json()
        access_token = token_json.get('access_token')
        id_token = token_json.get('id_token')

        if not access_token:
            return Response({"status": "failed", "message": "No access token returned from Google."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch user info
        try:
            userinfo_resp = requests.get('https://openidconnect.googleapis.com/v1/userinfo', headers={'Authorization': f'Bearer {access_token}'}, timeout=10)
            userinfo_resp.raise_for_status()
            userinfo = userinfo_resp.json()
        except Exception as e:
            return Response({"status": "failed", "message": f"Failed to fetch user info: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        email = userinfo.get('email')
        first_name = userinfo.get('given_name', '')
        last_name = userinfo.get('family_name', '')

        if not email:
            return Response({"status": "failed", "message": "Google account did not return an email."}, status=status.HTTP_400_BAD_REQUEST)

        # Create or get a Django user
        try:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'is_active': True,
                },
            )
        except Exception as e:
            return Response({"status": "failed", "message": f"Failed to create/get user: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Optionally update fields on existing user
        if not created:
            updated = False
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                updated = True
            if last_name and user.last_name != last_name:
                user.last_name = last_name
                updated = True
            if updated:
                user.save()

        serializer = UserSerializer(user)

        return Response({
            "status": "success",
            "message": "Google sign-in successful.",
            "data": {
                "user": serializer.data,
                "tokens": token_json,
                "userinfo": userinfo,
            }
        }, status=status.HTTP_200_OK)



class AuthGoogleOAuthStartView(APIView):

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        client_id = config('GOOGLE_CLIENT_ID', default=None)
        redirect_uri = config('GOOGLE_REDIRECT_URI', default='http://localhost:8000/auth/oauth2callback')
        scope = 'openid email profile'
        auth_url = (
            'https://accounts.google.com/o/oauth2/v2/auth'
            f'?response_type=code&client_id={client_id}'
            f'&redirect_uri={redirect_uri}'
            f'&scope={scope.replace(" ", "%20")}&access_type=offline&prompt=consent'
        )

        # Redirect the user agent to Google's consent screen
        return redirect(auth_url)
