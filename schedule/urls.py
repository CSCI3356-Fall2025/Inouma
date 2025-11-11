from django.urls import path
from . import views

urlpatterns = [
    path("api/shifts/", views.list_shifts_json, name="list_shifts_json"),
    path("api/shifts/clear/", views.clear_shifts, name="clear_shifts"),
    path("api/unavailability/add/", views.add_unavailability, name="add_unavailability"),
    path("api/auto/", views.auto_schedule, name="auto_schedule"),
    path("api/window/", views.window_status, name="window_status"),
    path("api/window/set/", views.window_set, name="window_set"),
    path("api/export.ics", views.export_ics, name="export_ics"),
]