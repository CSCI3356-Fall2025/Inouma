from django.db import models
from django.conf import settings
from machines.models import Machine


class Reservation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="machine_reservations",
    )
    machine = models.ForeignKey(
        Machine,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    reservation_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    purpose = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["reservation_date", "start_time"]

    def __str__(self):
        return f"{self.machine} reserved by {self.user} on {self.reservation_date} {self.start_time}-{self.end_time}"
