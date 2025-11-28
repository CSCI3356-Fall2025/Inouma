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
    path('staff/machines/directory/', views.staff_machine_directory, name='staff_machine_directory'),  # NEW
    path('staff/machines/add/', views.machine_management, name='add_machine'),
    path('staff/machines/edit/<int:machine_id>/', views.edit_machine, name='edit_machine'),
    path('staff/machines/detail/<int:machine_id>/', views.machine_detail_api, name='machine_detail_api'),  # NEW
    path('staff/remove-machine/<int:machine_id>/', views.remove_machine, name='remove_machine'),
    
    # API endpoints
    path('api/machine-suggestions/', views.get_machine_suggestions, name='machine_suggestions'),
    path('api/check-duplicate/', views.check_duplicate_machine, name='check_duplicate_machine'),
    path('api/search-suggestions/', views.get_search_suggestions, name='search_suggestions'),  # NEW
]