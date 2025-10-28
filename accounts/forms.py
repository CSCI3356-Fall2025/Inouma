from django import forms
from .models import StudentProfile

class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ["major1", "major2", "minor1", "minor2"]
        widgets = {
            "major1": forms.TextInput(attrs={"placeholder": "Major"}),
            "major2": forms.TextInput(attrs={"placeholder": "Optional second major"}),
            "minor1": forms.TextInput(attrs={"placeholder": "Optional Minor"}),
            "minor2": forms.TextInput(attrs={"placeholder": "Optional second minor"}),
        }