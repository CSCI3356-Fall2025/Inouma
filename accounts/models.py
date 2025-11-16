from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid


# User Manager
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email must be set'))

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)


# User Model
class User(AbstractUser):
    ROLE_CHOICES = (
        ('User', 'User'),
        ('Collaborator', 'Collaborator'),
        ('Team Member', 'Team Member'),
        ('Staff', 'Staff'),
    )


    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('email address'), unique=True)
    username = None
    firebase_uid = models.CharField(max_length=255, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='User')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    class Meta:
        db_table = 'user'
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-date_joined']


# Customizable Student Profile
class StudentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile")
    major1 = models.TextField(blank=True)
    major2 = models.TextField(blank=True)
    minor1 = models.TextField(blank=True)
    minor2 = models.TextField(blank=True)
    birthday = models.DateField(null=True, blank=True, help_text="Date of birth")
    graduation_year = models.IntegerField(null=True, blank=True, help_text="Expected graduation year (e.g., 2025)")
    role_specification = models.CharField(max_length=100, blank=True, help_text="Additional role details (e.g., 'Undergraduate', 'Graduate Student')")

    def __str__(self):
        return f"Student Profile for {self.user.email}"
    
    def clean(self):
        """Validate graduation year is reasonable"""
        from django.core.exceptions import ValidationError
        if self.graduation_year:
            current_year = 2024 
            if self.graduation_year < 1900 or self.graduation_year > current_year + 10:
                raise ValidationError({
                    'graduation_year': f'Graduation year must be between 1900 and {current_year + 10}'
                })


# Customizable Trainer Profile
class TrainerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trainer_profile")
    specialty = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    certifications = models.TextField(blank=True)

    def __str__(self):
        return f"Trainer Profile for {self.user.email}"


# Auto Create Profiles
@receiver(post_save, sender=User)
def create_role_profile(sender, instance, created, **kwargs):
    if created:
        if instance.role in ['User', 'Collaborator']:
            StudentProfile.objects.create(user=instance)
        elif instance.role in ['Team Member', 'Trainer']:
            TrainerProfile.objects.create(user=instance)

class Machine(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    required_training_level = models.PositiveSmallIntegerField(default=1)  # aligns with Level 1/2/3 in prototypes

    def __str__(self):
        return self.name


class MachineInstance(models.Model):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name="instances")
    nickname = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=30, default="available")  # e.g., available / maintenance / down

    def __str__(self):
        return f"{self.machine.name} ({self.nickname or self.id})"


class TrainingReservation(models.Model):
    """
    Student books a training session with a trainer on a specific machine instance and time span.
    Overlap for the same trainer is disallowed (Delivery 4 requirement).
    """
    STATUS_CHOICES = (
        ("CONFIRMED", "Confirmed"),
        ("CANCELED", "Canceled"),
    )
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="training_reservations")
    trainer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trainer_reservations")
    machine_instance = models.ForeignKey(MachineInstance, on_delete=models.PROTECT, related_name="training_reservations")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="CONFIRMED")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["trainer", "start_time"]),
            models.Index(fields=["trainer", "end_time"]),
        ]

    def __str__(self):
        return f"{self.student} with {self.trainer} @ {self.start_time}"

    def overlaps(self, other_start, other_end):
        return not (self.end_time <= other_start or self.start_time >= other_end)