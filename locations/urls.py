from django.urls import path
from . import views

urlpatterns = [
    path('', views.location_management, name='location_management'),
    path('add/', views.add_location, name='add_location'),
    path('<int:location_id>/edit/', views.edit_location, name='edit_location'),
    path('<int:location_id>/delete/', views.delete_location, name='delete_location'),
]