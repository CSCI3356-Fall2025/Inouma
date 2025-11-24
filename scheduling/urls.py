from django.urls import path
from . import views

urlpatterns = [
    path('staff/scheduling', views.schedule_management, name='schedule_management'),
]