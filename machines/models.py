from django.db import models
import os


class TrainingType(models.Model):
    """
    Represents a specific training / credential, similar to QReserve tags.

    Examples:
    - "Laser Cutter Training"
    - "Intro to 3D Printing"
    - "Wood Shop Safety"
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Machine(models.Model):
    """
    Represents a specific machine/equipment in the makerspace.
    """
    
    CATEGORY_CHOICES = [
        ('Laser', 'Laser'),
        ('Vinyl', 'Vinyl'),
        ('Woodworking', 'Woodworking'),
        ('Textile', 'Textile'),
        ('Metalworking', 'Metalworking'),
        ('3D Printing', '3D Printing'),
        ('Electronics', 'Electronics'),
    ]

    # Basic identification
    name = models.CharField(
        max_length=100,
        help_text="Unique identifier, for example 'Ultimaker #1', 'Epilog Laser #2'."
    )
    machine_name = models.CharField(
        max_length=200,
        help_text="Model or type, for example 'Ultimaker S5', 'Epilog Fusion Pro'."
    )

    # Category and Location
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    location = models.ForeignKey(
        'locations.Location',
        on_delete=models.CASCADE,
        related_name='machines',
        help_text="Physical location of this machine"
    )
    
    description = models.TextField(blank=True, null=True)

    # Floorplan positioning (stored as percentages 0-100 for responsive positioning)
    map_position_x = models.FloatField(
        null=True, 
        blank=True,
        help_text="X position on floorplan (0-100%)"
    )
    map_position_y = models.FloatField(
        null=True, 
        blank=True,
        help_text="Y position on floorplan (0-100%)"
    )

    # Optional technical details
    mac_address = models.CharField(
        max_length=17,
        blank=True,
        null=True,
        help_text="MAC address, for example 00:1B:44:11:3A:B7."
    )
    year_bought = models.IntegerField(
        blank=True,
        null=True,
        help_text="Year this machine was purchased."
    )

    # Image
    image = models.ImageField(
        upload_to='machines/images/',
        blank=True,
        null=True,
        help_text="Upload a photo of the machine."
    )

    # Legacy training level flags (kept for backwards compatibility)
    requires_level_1 = models.BooleanField(default=False)
    requires_level_2 = models.BooleanField(default=False)
    requires_level_3 = models.BooleanField(default=False)

    # Modern training requirements (Delivery 6)
    required_trainings = models.ManyToManyField(
        TrainingType,
        blank=True,
        related_name="machines",
        help_text="Specific training(s) a student must complete to use this machine."
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'machine_name', 'name']

    def __str__(self):
        return f"{self.machine_name} - {self.name}"

    def get_image_url(self):
        """
        Returns the URL of the machine's image or a default image.
        """
        if self.image:
            return self.image.url
        return '/media/machines/default_machine.jpg'
    
    def has_map_position(self):
        """
        Check if this machine has been positioned on a floorplan.
        """
        return self.map_position_x is not None and self.map_position_y is not None