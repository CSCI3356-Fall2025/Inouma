from django.urls import path
from . import views

app_name = 'scheduling'

urlpatterns = [
    # Landing page
    path('staff/', views.schedule_landing, name='schedule_landing'),
    
    # Main pages
    path('staff/view/', views.view_schedule, name='view_schedule'),
    path('staff/configure/', views.configure_semester, name='configure_semester'),
    path('staff/availability/', views.manage_availability, name='manage_availability'),
    path('staff/requests/', views.review_requests, name='review_requests'),
    path('staff/auto-schedule-page/', views.auto_schedule_page, name='auto_schedule'),
    path('staff/semesters/', views.manage_semesters, name='manage_semesters'),
    path('staff/publish/', views.publish_schedule_page, name='publish_schedule'),
    
    # Actions
    path('staff/auto-schedule/', views.run_auto_scheduler, name='run_auto_scheduler'),
    path('staff/clear/<int:semester_id>/', views.clear_schedule, name='clear_schedule'),
    
    # API Endpoints - Semesters
    path('api/semesters/', views.api_get_semesters, name='api_semesters'),
    path('api/semesters/save/', views.api_save_semester, name='api_save_semester'),
    path('api/semesters/set-active/', views.api_set_active_semester, name='api_set_active_semester'),
    path('api/semesters/archive/', views.api_archive_semester, name='api_archive_semester'),
    path('api/semesters/unarchive/', views.api_unarchive_semester, name='api_unarchive_semester'),
    path('api/semesters/delete/', views.api_delete_semester, name='api_delete_semester'),
    
    # API Endpoints - Semester Config
    path('api/semester/<int:semester_id>/', views.api_get_semester_config, name='api_semester_detail'),
    path('api/semester/<int:semester_id>/config/', views.api_get_semester_config, name='api_semester_config'),
    path('api/semester/config/save/', views.api_save_semester_config, name='api_save_semester_config'),
    
    # API Endpoints - Location Groups
    path('api/location-groups/', views.api_get_location_groups, name='api_location_groups'),
    path('api/location-groups/save/', views.api_save_location_group, name='api_save_location_group'),
    path('api/location-groups/<int:group_id>/delete/', views.api_delete_location_group, name='api_delete_location_group'),
    
    # API Endpoints - Schedule Data
    path('api/weeks/', views.api_get_weeks, name='api_weeks'),
    path('api/shifts/', views.api_get_shifts, name='api_shifts'),
    path('api/team-members/', views.api_get_team_members, name='api_team_members'),
    path('api/team-members/save/', views.api_save_team_member, name='api_save_team_member'),
    path('api/categories/', views.api_get_categories, name='api_categories'),
    path('api/stats/', views.api_shift_stats, name='api_stats'),
    
    # API Endpoints - Publish Schedule
    path('api/publish/', views.api_publish_schedule, name='api_publish'),
    path('api/publish/history/', views.api_get_publish_history, name='api_publish_history'),
    
    # API Endpoints - Review Requests
    path('api/requests/', views.api_get_requests, name='api_requests'),
    path('api/requests/approve/', views.api_approve_request, name='api_approve_request'),
    path('api/requests/reject/', views.api_reject_request, name='api_reject_request'),
    
    # Team Member URLs
    path('my-availability/', views.my_availability, name='my_availability'),
    path('my-schedule/', views.my_schedule, name='my_schedule'),
]