from django.contrib import admin
from .models import Shift, Unavailability, ScheduleWindow

# Register your models here.
@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ("date", "start_time", "end_time", "trainer", "team")
    list_filter = ("date", "team")
    search_fields = ("trainer__username", "trainer__first_name", "trainer__last_name")

@admin.register(Unavailability)
class UnavailabilityAdmin(admin.ModelAdmin):
    list_display = ("trainer", "weekday", "start_time", "end_time")
    list_filter = ("weekday",)
    search_fields = ("trainer__username", "trainer__first_name", "trainer__last_name")

@admin.register(ScheduleWindow)
class ScheduleWindowAdmin(admin.ModelAdmin):
    list_display = ("id", "is_open")