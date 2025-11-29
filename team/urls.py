from django.urls import path
from . import views

app_name = 'team'

urlpatterns = [
    # Team Directory Page
    path('directory/', views.team_directory, name='team_directory'),
    
    # API Endpoints
    path('api/members/', views.api_get_team_members, name='api_members'),
    path('api/members/save/', views.api_save_team_member, name='api_save_member'),
    path('api/groups/', views.api_get_team_groups, name='api_groups'),
    path('api/send-birthday-emails/', views.api_send_birthday_emails, name='api_send_birthday_emails'),
]