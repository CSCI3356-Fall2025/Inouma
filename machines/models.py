from django.db import models
import os

class Machine(models.Model):
    CATEGORY_CHOICES = [
        ('Laser', 'Laser'),
        ('Vinyl', 'Vinyl'),
        ('Woodworking', 'Woodworking'),
        ('Textile', 'Textile'),
        ('Metalworking', 'Metalworking'),
        ('3D Printing', '3D Printing'),
        ('Electronics', 'Electronics'),
    ]
    
    LOCATION_CHOICES = [
        ('Hatch Front (2nd Floor)', 'Hatch Front (2nd Floor)'),
        ('Hatch Back (2nd Floor)', 'Hatch Back (2nd Floor)'),
        ('Prototyping Studio (3rd Floor)', 'Prototyping Studio (3rd Floor)'),
        ('Prototyping Shop (3rd Floor)', 'Prototyping Shop (3rd Floor)'),
    ]
    
    # Basic Information
    name = models.CharField(max_length=100, help_text="Unique identifier (e.g., 'Ultimaker #1', 'Ultimaker #2')")
    machine_name = models.CharField(max_length=200, help_text="Model/Type (e.g., 'Ultimaker S5')")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    location = models.CharField(max_length=100, choices=LOCATION_CHOICES)
    description = models.TextField(blank=True, null=True)
    
    # Optional Technical Details
    mac_address = models.CharField(max_length=17, blank=True, null=True, help_text="MAC address (e.g., 00:1B:44:11:3A:B7)")
    year_bought = models.IntegerField(blank=True, null=True, help_text="Year the machine was purchased")
    
    # Image field - either use existing image or upload new one
    image = models.ImageField(upload_to='machines/images/', blank=True, null=True)
    
    # Training level requirements
    requires_level_1 = models.BooleanField(default=False)
    requires_level_2 = models.BooleanField(default=False)
    requires_level_3 = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.machine_name} ({self.category})"
    
    def get_image_url(self):
        """Returns the URL of the machine's image or default"""
        if self.image:
            return self.image.url
        else:
            return '/media/machines/default_machine.jpg'
        
    # Floorplan positioning (store as percentages for responsive positioning)
    map_position_x = models.FloatField(null=True, blank=True, help_text="X position on floorplan (0-100%)")
    map_position_y = models.FloatField(null=True, blank=True, help_text="Y position on floorplan (0-100%)")
    
    def has_map_position(self):
        return self.map_position_x is not None and self.map_position_y is not None
  
  