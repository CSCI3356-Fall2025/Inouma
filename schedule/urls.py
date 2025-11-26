from django.urls import path
from . import views

urlpatterns = [
    path("api/shifts/clear/", views.clear_shifts, name="clear_shifts"),
    path("api/unavailability/add/", views.add_unavailability, name="add_unavailability"),
    path("api/auto/", views.auto_schedule, name="auto_schedule"),
    path("api/window/", views.window_status, name="window_status"),
    path("api/window/set/", views.window_set, name="window_set"),
    path("api/export.ics", views.export_ics, name="export_ics"),
    path("api/shifts/", views.api_shifts, name="api_shifts"),
    path("api/semesters/", views.get_semesters, name="get_semesters"),
    path("api/weeks/", views.get_weeks, name="get_weeks"),
    path("api/trainers/", views.get_trainers, name="get_trainers"),
]