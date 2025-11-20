from django.db import models

class Location(models.Model):
    name = models.CharField(max_length=100, help_text="e.g., Hatch Front, Prototyping Studio")
    building = models.CharField(max_length=200, help_text="e.g., 245 Beacon St")
    floor = models.CharField(max_length=50, help_text="e.g., 3rd Floor")
    num_stations = models.IntegerField(help_text="Number of tables/workstations")
    capacity = models.IntegerField(help_text="Maximum number of people")
    machine_types = models.TextField(
        help_text="Comma-separated list (e.g., Woodworking, Metalworking, 3D Printing)"
    )
    floorplan_image = models.ImageField(
        upload_to='floorplans/', 
        null=True, 
        blank=True,
        help_text="Upload a floorplan image for this location"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['building', 'floor', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.building} ({self.floor})"
    
    def get_machine_types_list(self):
        """Return machine types as a list"""
        return [t.strip() for t in self.machine_types.split(',') if t.strip()]