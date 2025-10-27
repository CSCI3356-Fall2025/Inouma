from rest_framework import authentication
from .firebase_exceptions import NoAuthToken, InvalidAuthToken, FirebaseError, EmailVerification
from firebase_admin import auth, credentials
from accounts.models import User
from django.db import IntegrityError


class FirebaseAuthentication(authentication.BaseAuthentication):
    keyword = 'Bearer'

    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')

        if not auth_header:
            raise NoAuthToken("No authentication token provided.")

        id_token = auth_header.split(' ').pop()
        decoded_token = None

        # Verify the Firebase ID token
        try:
            decoded_token = auth.verify_id_token(id_token)
        except Exception:
            raise InvalidAuthToken("Invalid authentication token provided.")

        if not id_token or not decoded_token:
            return None

        # Check email verification (optional if you disabled Firebase email verification)
        email_verified = decoded_token.get('email_verified', True)
        if not email_verified:
            raise EmailVerification("Email not verified. Please verify your email address.")

        # Extract UID
        uid = decoded_token.get('uid')
        if not uid:
            raise FirebaseError("The user provided with the auth token is not a Firebase user. It has no Firebase UID.")

        # Create or get the corresponding Django user
        try:
            user, _ = User.objects.get_or_create(
                firebase_uid=uid,
                defaults={
                    "first_name": decoded_token.get("name", ""),
                    "phone_number": decoded_token.get("phone_number", ""),
                    "email": decoded_token.get("email", ""),
                },
            )
        except IntegrityError as e:
            raise FirebaseError(f"Error creating or accessing user data: {e}")
        except Exception as e:
            raise FirebaseError(f"Error accessing user data: {e}")

        return (user, None)
