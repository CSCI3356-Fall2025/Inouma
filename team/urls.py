from django.urls import path
from . import views

app_name = 'team'

urlpatterns = [
    # Team Directory Page
    path('directory/', views.team_directory, name='team_directory'),
    
    # API Endpoints
    path('api/members/', views.api_get_team_members, name='api_members'),
    path('api/members/create/', views.api_create_member, name='api_create_member'),
    path('api/members/<str:member_id>/update/', views.api_update_member, name='api_update_member'),
    path('api/members/archive/', views.api_archive_members, name='api_archive_members'),
    path('api/members/delete/', views.api_delete_members, name='api_delete_members'),
    path('api/members/save/', views.api_save_team_member, name='api_save_member'),
    path('api/members/bulk-assign/', views.api_bulk_assign_group, name='api_bulk_assign'),
    path('api/members/bulk-team-assign/', views.api_bulk_team_assign, name='api_bulk_team_assign'),
    path('api/members/update-group/', views.api_update_member_group, name='api_update_member_group'),
    path('api/groups/', views.api_get_team_groups, name='api_groups'),
    path('api/machine-categories/', views.api_get_machine_categories, name='api_machine_categories'),
    path('api/send-birthday-emails/', views.api_send_birthday_emails, name='api_send_birthday_emails'),
]