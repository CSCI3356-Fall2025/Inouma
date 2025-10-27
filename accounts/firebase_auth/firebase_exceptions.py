from rest_framework.exceptions import APIException
from rest_framework import status


class NoAuthToken(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'No authentication token provided.'
    default_code = 'no_auth_token'


class InvalidAuthToken(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Invalid authentication token provided.'
    default_code = 'invalid_auth_token'


class FirebaseError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'The user provided with auth token is not a Firebase user. It has no Firebase UID.'
    default_code = 'no_firebase_uid'


class EmailVerification(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Email not verified.'
    default_code = 'email_not_verified'
