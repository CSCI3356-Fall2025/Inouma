# social/urls.py
"""
URL configuration for social features.
"""

from django.urls import path
from . import views

app_name = 'social'

urlpatterns = [
    # Page views
    path('projects/', views.projects_feed, name='projects_feed'),
    path('projects/create/', views.create_project, name='create_project'),
    path('projects/<int:project_id>/', views.project_detail, name='project_detail'),
    path('projects/<int:project_id>/edit/', views.edit_project, name='edit_project'),
    path('friends/', views.friends_page, name='friends'),
    path('profile/<int:user_id>/', views.user_profile, name='user_profile'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    
    # Project APIs
    path('api/projects/', views.api_projects_list, name='api_projects_list'),
    path('api/projects/create/', views.api_create_project, name='api_create_project'),
    path('api/projects/<int:project_id>/', views.api_project_detail, name='api_project_detail'),
    path('api/projects/<int:project_id>/update/', views.api_update_project, name='api_update_project'),
    path('api/projects/<int:project_id>/delete/', views.api_delete_project, name='api_delete_project'),
    path('api/projects/<int:project_id>/like/', views.api_like_project, name='api_like_project'),
    path('api/projects/<int:project_id>/comments/', views.api_project_comments, name='api_project_comments'),
    path('api/projects/<int:project_id>/comments/add/', views.api_add_comment, name='api_add_comment'),
    
    # Friend APIs
    path('api/friends/', views.api_friends_list, name='api_friends_list'),
    path('api/friends/request/', views.api_send_friend_request, name='api_send_friend_request'),
    path('api/friends/<int:friendship_id>/respond/', views.api_respond_friend_request, name='api_respond_friend_request'),
    path('api/friends/<int:friendship_id>/remove/', views.api_remove_friend, name='api_remove_friend'),
    path('api/users/search/', views.api_search_users, name='api_search_users'),
    
    # Profile & Stats APIs
    path('api/profile/<int:user_id>/', views.api_user_profile, name='api_user_profile'),
    path('api/my-stats/', views.api_my_stats, name='api_my_stats'),
    path('api/leaderboard/', views.api_leaderboard, name='api_leaderboard'),
]