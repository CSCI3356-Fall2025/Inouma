from django.contrib import admin
from .models import Reservation

# Register your models here.

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "machine",
        "reservation_date",
        "start_time",
        "end_time",
        "purpose",
        "created_at",
    )
    list_filter = ("machine", "reservation_date")
    search_fields = ("user__username", "machine__name", "purpose")