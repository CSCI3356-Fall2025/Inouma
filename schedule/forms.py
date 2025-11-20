from django import forms
from .models import Unavailability, ScheduleWindow

class UnavailabilityForm(forms.ModelForm):
    class Meta:
        model = Unavailability
        fields = ["weekday", "start_time", "end_time"]

class ScheduleWindowForm(forms.ModelForm):
    class Meta:
        model = ScheduleWindow
        fields = ["opens_at", "closes_at", "is_open"]