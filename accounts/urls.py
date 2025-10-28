from django.urls import path
from . import views
from .views import (
    AuthCreateNewUserView,
    AuthLoginExistingUserView,
    AuthGoogleOAuthCallbackView,
    AuthGoogleOAuthStartView,
    login_view,
    logout_view,
)

urlpatterns = [
    # Paths are relative so the project can include this file at '/auth/' or '/api/'
    path('sign-up/', AuthCreateNewUserView.as_view(), name='auth-create-user'),
    path('sign-in/', AuthLoginExistingUserView.as_view(), name='auth-login-user'),
    path('login/', AuthGoogleOAuthStartView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('google/callback/', AuthGoogleOAuthCallbackView.as_view(),
         name='auth-google-callback'),
    path('oauth2callback', AuthGoogleOAuthCallbackView.as_view(),
         name='oauth2callback'),
    path('google/start/', AuthGoogleOAuthStartView.as_view(),
         name='auth-google-start'),
     path("profile/", views.profile_detail, name="profile_detail"),
     path("profile/edit/", views.profile_edit, name="profile_edit"),
]
