from django.urls import path
from . import views
from .views_booking_page import training_booking_page_by_name
from .views import (
    AuthCreateNewUserView,
    AuthLoginExistingUserView,
    AuthGoogleOAuthCallbackView,
    AuthGoogleOAuthStartView,
    login_view,
    logout_view,
    TrainingReservationView,
    TrainerAvailabilityView,
    profile_detail,
    profile_edit,
)

urlpatterns = [
    # auth
    path('sign-up/', AuthCreateNewUserView.as_view(), name='auth-create-user'),
    path('sign-in/', AuthLoginExistingUserView.as_view(), name='auth-login-user'),

    path('login/', AuthGoogleOAuthStartView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    
    path('google/callback/', AuthGoogleOAuthCallbackView.as_view(), name='auth-google-callback'),
    path('oauth2callback', AuthGoogleOAuthCallbackView.as_view(), name='oauth2callback'),
    path('google/start/', AuthGoogleOAuthStartView.as_view(), name='auth-google-start'),

    # profiles
    path('profile/', views.profile_detail, name='profile_detail'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),

    # 🔹 Booking page by NAME (auto-seeds)
    path('book/machine/by-name/<slug:machine_slug>/', training_booking_page_by_name,
         name='training_booking_by_name'),

    # APIs
    path('api/training-reservations/', TrainingReservationView.as_view(), name='training_reservations'),
    path("api/trainers/<uuid:trainer_id>/availability/", TrainerAvailabilityView.as_view(), name="trainer_availability",),

    # About Page
    path('about/', views.about_hatchery, name='about_hatchery'),
]
