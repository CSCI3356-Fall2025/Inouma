from django import forms
from .models import Location

class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ['name', 'building', 'floor', 'num_stations', 'capacity', 'machine_types', 'floorplan_image']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g., Hatch Front'}),
            'building': forms.TextInput(attrs={'placeholder': 'e.g., 245 Beacon St'}),
            'floor': forms.TextInput(attrs={'placeholder': 'e.g., 3rd Floor'}),
            'num_stations': forms.NumberInput(attrs={'min': '1'}),
            'capacity': forms.NumberInput(attrs={'min': '1'}),
            'machine_types': forms.Textarea(attrs={
                'placeholder': 'e.g., Woodworking, Metalworking, 3D Printing',
                'rows': 3
            }),
            'floorplan_image': forms.FileInput(attrs={'accept': 'image/*'})
        }