from django.db import models
from django.conf import settings
import os


class MachineCategory(models.Model):
    """
    Dynamic machine categories that can be managed by staff/admin.
    Examples: Laser, 3D Printing, Woodworking, etc.
    """
    name = models.CharField(max_length=50, unique=True, help_text="Category name (e.g., 'Laser', '3D Printing')")
    description = models.TextField(blank=True, help_text="Description of this category")
    icon = models.CharField(max_length=10, blank=True, help_text="Emoji icon for the category")
    color = models.CharField(max_length=20, blank=True, default='#293242', help_text="Color code for UI display")
    display_order = models.PositiveIntegerField(default=0, help_text="Order in which to display categories")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'Machine Category'
        verbose_name_plural = 'Machine Categories'
    
    def __str__(self):
        return self.name
    
    @property
    def machine_count(self):
        return self.machines.count()


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


class Training(models.Model):
    """
    Training definition - a specific training course that users can complete.
    Trainings have levels (1, 2, 3) and are assigned to machine types.
    """
    LEVEL_CHOICES = [
        (1, 'Level 1 - Introduction'),
        (2, 'Level 2 - Intermediate'),
        (3, 'Level 3 - Advanced'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('archived', 'Archived'),
        ('draft', 'Draft'),
    ]
    
    name = models.CharField(max_length=200, help_text="Training name (e.g., 'Intro to 3D Printing')")
    description = models.TextField(blank=True, help_text="Detailed description of what this training covers")
    
    level = models.PositiveSmallIntegerField(choices=LEVEL_CHOICES, default=1)
    category = models.CharField(max_length=50, help_text="Category (e.g., '3D Printing', 'Laser')")
    
    # Machine types this training applies to (stored as list of machine_name strings)
    machine_type_names = models.JSONField(
        default=list,
        blank=True,
        help_text="List of machine_name values this training qualifies users for"
    )
    
    # Prerequisites - other trainings required before this one
    prerequisites = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='unlocks',
        blank=True,
        help_text="Trainings required before taking this one"
    )
    
    # Training details
    duration_minutes = models.PositiveIntegerField(default=60, help_text="Expected duration in minutes")
    max_participants = models.PositiveIntegerField(default=4, help_text="Maximum participants per session")
    
    # Content
    materials_url = models.URLField(blank=True, help_text="Link to training materials")
    video_url = models.URLField(blank=True, help_text="Link to training video")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_trainings'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'level', 'name']
        verbose_name = 'Training'
        verbose_name_plural = 'Trainings'
    
    def __str__(self):
        return f"{self.name} (Level {self.level})"
    
    @property
    def level_display(self):
        return dict(self.LEVEL_CHOICES).get(self.level, f'Level {self.level}')


class UserTrainingRecord(models.Model):
    """
    Records a user's completion of a training.
    This is what qualifies them to use certain machines.
    """
    STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('in_progress', 'In Progress'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='training_records'
    )
    training = models.ForeignKey(
        Training,
        on_delete=models.CASCADE,
        related_name='user_records'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    
    # Completion details
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Optional expiration date")
    
    # Who conducted/verified the training
    trainer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conducted_trainings'
    )
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-completed_at']
        unique_together = ['user', 'training']
        verbose_name = 'User Training Record'
        verbose_name_plural = 'User Training Records'
    
    def __str__(self):
        return f"{self.user} - {self.training}"
    
    @property
    def is_valid(self):
        """Check if training is currently valid (completed and not expired)"""
        if self.status != 'completed':
            return False
        if self.expires_at:
            from django.utils import timezone
            return self.expires_at > timezone.now()
        return True


class Machine(models.Model):
    """
    Represents a specific machine/equipment in the makerspace.
    """

    # Basic identification
    name = models.CharField(
        max_length=100,
        help_text="Unique identifier, for example 'Ultimaker #1', 'Epilog Laser #2'."
    )
    machine_name = models.CharField(
        max_length=200,
        help_text="Model or type, for example 'Ultimaker S5', 'Epilog Fusion Pro'."
    )

    # OLD Category field - keep as-is for now
    CATEGORY_CHOICES = [
        ('Laser', 'Laser'),
        ('Vinyl', 'Vinyl'),
        ('Woodworking', 'Woodworking'),
        ('Textile', 'Textile'),
        ('Metalworking', 'Metalworking'),
        ('3D Printing', '3D Printing'),
        ('Electronics', 'Electronics'),
    ]
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    
    # NEW Category FK - add as separate field, will replace 'category' later
    category_fk = models.ForeignKey(
        MachineCategory,
        on_delete=models.PROTECT,
        related_name='machines',
        null=True,
        blank=True,
        help_text="Machine category (new)"
    )
    
    # Location
    location = models.ForeignKey(
        'locations.Location',
        on_delete=models.CASCADE,
        related_name='machines',
        help_text="Physical location of this machine"
    )
    
    description = models.TextField(blank=True, null=True)
    
    # Additional machine details
    manufacturer = models.CharField(
        max_length=100,
        blank=True,
        help_text="Manufacturer name (e.g., Ultimaker, Prusa Research)"
    )
    model_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Model number (e.g., S5, MK3S+)"
    )
    documentation_url = models.URLField(
        blank=True,
        help_text="Link to user manual or documentation"
    )

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
    
    def get_required_trainings(self):
        """
        Get all trainings required to use this machine.
        Checks both the new Training system (via machine_type_names) and legacy TrainingType.
        """
        trainings = []

        # New system: trainings whose machine_type_names list includes this machine's name
        from .models import Training
        all_trainings = Training.objects.filter(status='active')
        new_trainings = [
            t for t in all_trainings
            if self.machine_name in (t.machine_type_names or [])
        ]
        trainings.extend(new_trainings)

        # Legacy system: Get from required_trainings (ManyToMany)
        trainings.extend(list(self.required_trainings.all()))

        return trainings
