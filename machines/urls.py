from django.urls import path
from . import views

urlpatterns = [
    # User-facing machine directory
    path('machines/', views.machine_directory, name='machine_directory'),
    path('category/<str:category>/', views.category_detail, name='category_detail'),
    path('type/<str:machine_type>/', views.machine_type_detail, name='machine_type_detail'),
    path('detail/<int:machine_id>/', views.machine_detail, name='machine_detail'),
    
    # Staff dashboard and management
    path('staff/', views.staff_dashboard, name='staff_dashboard'),
    path('staff/machines/', views.machine_management_landing, name='machine_management'),
    path('staff/machines/directory/', views.staff_machine_directory, name='staff_machine_directory'),
    path('staff/machines/add/', views.machine_management, name='add_machine'),
    path('staff/machines/edit/<int:machine_id>/', views.edit_machine, name='edit_machine'),
    path('staff/machines/detail/<int:machine_id>/', views.machine_detail_api, name='machine_detail_api'),
    path('staff/remove-machine/<int:machine_id>/', views.remove_machine, name='remove_machine'),
    
    # Category Management
    path('staff/machines/categories/', views.manage_categories, name='manage_categories'),
    
    # Training Management
    path('staff/training/', views.training_management, name='training_management'),
    
    # Category API endpoints
    path('api/categories/', views.api_get_categories, name='api_categories'),
    path('api/categories/create/', views.api_create_category, name='api_create_category'),
    path('api/categories/<int:category_id>/update/', views.api_update_category, name='api_update_category'),
    path('api/categories/<int:category_id>/delete/', views.api_delete_category, name='api_delete_category'),
    
    # Training API endpoints
    path('api/trainings/', views.api_get_trainings, name='api_trainings'),
    path('api/trainings/create/', views.api_create_training, name='api_create_training'),
    path('api/trainings/<int:training_id>/update/', views.api_update_training, name='api_update_training'),
    path('api/trainings/<int:training_id>/archive/', views.api_archive_training, name='api_archive_training'),
    path('api/trainings/<int:training_id>/delete/', views.api_delete_training, name='api_delete_training'),
    path('api/trainings/bulk/', views.api_bulk_training_action, name='api_bulk_training_action'),
    
    # Existing Machine Types API (reads from Machine.machine_name field)
    path('api/existing-machine-types/', views.api_get_existing_machine_types, name='api_existing_machine_types'),
    
    # Existing API endpoints
    path('api/machine-suggestions/', views.get_machine_suggestions, name='machine_suggestions'),
    path('api/check-duplicate/', views.check_duplicate_machine, name='check_duplicate_machine'),
    path('api/search-suggestions/', views.get_search_suggestions, name='search_suggestions'),
    # Reporting a machine as broken (user-facing)
    path('report-broken/<int:machine_id>/', views.report_broken, name='report_broken'),
]
