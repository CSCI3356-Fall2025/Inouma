from django.db import models
from django.conf import settings

# Create your models here.
WEEKDAYS = [(i, name) for i, name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])]

class ScheduleWindow(models.Model):
    is_open = models.BooleanField(default=True)

class Unavailability(models.Model):
    trainer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="unavailabilities")
    weekday = models.IntegerField(choices=WEEKDAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ["weekday", "start_time"]

class Shift(models.Model):
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    trainer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shifts")
    team = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        ordering = ["date", "start_time"]
        unique_together = ("date", "start_time", "end_time", "trainer")