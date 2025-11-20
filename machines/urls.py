from django.urls import path
from . import views

urlpatterns = [
    path('home', views.machine_directory, name='machine_directory'),
    path('staff/', views.staff_dashboard, name='staff_dashboard'),
    path('staff/machines/', views.machine_management, name='machine_management'),  # NEW - displays the form
    path('staff/add-machine/', views.add_machine, name='add_machine'),  # Handles POST submission
    path('staff/remove-machine/<int:machine_id>/', views.remove_machine, name='remove_machine'),
    path('api/machine-suggestions/', views.get_machine_suggestions, name='machine_suggestions'),
    path('api/check-duplicate/', views.check_duplicate_machine, name='check_duplicate_machine'),
    path('api/search-suggestions/', views.get_search_suggestions, name='search_suggestions'),
]