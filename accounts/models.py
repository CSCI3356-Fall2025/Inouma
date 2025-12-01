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
    
    SCHOOL_CHOICES = (
        ('', 'Select School'),
        ('MCAS', 'MCAS - Morrissey College of Arts and Sciences'),
        ('CSOM', 'CSOM - Carroll School of Management'),
        ('CSON', 'CSON - Connell School of Nursing'),
        ('LSEHD', 'LSEHD - Lynch School of Education and Human Development'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('email address'), unique=True)
    username = None
    firebase_uid = models.CharField(max_length=255, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='User')
    
    # Additional user information
    school = models.CharField(max_length=100, choices=SCHOOL_CHOICES, blank=True, help_text="School")
    department = models.CharField(max_length=100, blank=True, help_text="Department")
    profile_picture = models.ImageField(upload_to='users/profile_pictures/', blank=True, null=True, help_text="Profile picture")
    
    # Team Member specific fields (only apply when role is 'Team Member')
    is_team_lead = models.BooleanField(
        default=False, 
        help_text="Is this team member a team lead? (Team leads are automatically trainers)"
    )
    is_trainer = models.BooleanField(
        default=False, 
        help_text="Can this team member conduct training sessions?"
    )
    team_assignment = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="Machine category/team this member belongs to (required for team leads)"
    )
    
    def clean(self):
        """Validate team member fields"""
        from django.core.exceptions import ValidationError
        # Team lead and trainer flags only apply to Team Member role
        if self.role != 'Team Member':
            if self.is_team_lead:
                raise ValidationError({
                    'is_team_lead': 'Team Lead flag can only be set for users with Team Member role.'
                })
            if self.is_trainer:
                raise ValidationError({
                    'is_trainer': 'Trainer flag can only be set for users with Team Member role.'
                })
            if self.team_assignment:
                raise ValidationError({
                    'team_assignment': 'Team assignment can only be set for users with Team Member role.'
                })
        
        # Team leads must have a team assignment
        if self.is_team_lead and not self.team_assignment:
            raise ValidationError({
                'team_assignment': 'Team assignment is required for team leads.'
            })
    
    def save(self, *args, **kwargs):
        """Automatically clear team member fields if role is not Team Member, and set trainer if team lead"""
        if self.role != 'Team Member':
            self.is_team_lead = False
            self.is_trainer = False
            self.team_assignment = ''
        else:
            # Team leads are automatically trainers
            if self.is_team_lead:
                self.is_trainer = True
        super().save(*args, **kwargs)

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


class Certification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="certifications"
    )
    name = models.CharField(max_length=150)
    issued_at = models.DateField()
    expires_at = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} for {self.user.email}"


# Auto Create Profiles and Sync with Scheduling
@receiver(post_save, sender=User)
def create_role_profile(sender, instance, created, **kwargs):
    if created:
        if instance.role in ['User', 'Collaborator']:
            StudentProfile.objects.create(user=instance)
        elif instance.role in ['Team Member', 'Staff']:
            TrainerProfile.objects.create(user=instance)
    
    # Sync Team Member data with scheduling TeamMemberProfile
    if instance.role == 'Team Member':
        try:
            from scheduling.models import TeamMemberProfile
            profile, _ = TeamMemberProfile.objects.get_or_create(user=instance)
            
            # Sync the flags from User model
            profile.is_trainer = instance.is_trainer
            profile.is_team_lead = instance.is_team_lead
            profile.team = instance.team_assignment
            profile.save()
        except Exception as e:
            # Scheduling app might not be installed or migrated yet
            print(f"Could not sync TeamMemberProfile: {e}")


class Machine(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    required_training_level = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return self.name
    
    @classmethod
    def get_categories(cls):
        """Get all unique machine categories for team assignment"""
        return list(cls.objects.values_list('category', flat=True).distinct().exclude(category='').order_by('category'))


class MachineInstance(models.Model):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name="instances")
    nickname = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=30, default="available")

    def __str__(self):
        return f"{self.machine.name} ({self.nickname or self.id})"


class TrainingReservation(models.Model):
    """
    Student books a training session with a trainer on a specific machine instance and time span.
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


class TrainerAvailability(models.Model):
    """
    Weekly recurring availability blocks for each trainer.
    """
    WEEKDAYS = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    trainer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="weekly_available_blocks"
    )
    weekday = models.IntegerField(choices=WEEKDAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ["trainer", "weekday", "start_time"]

    def __str__(self):
        return f"{self.trainer.email} – {self.get_weekday_display()} {self.start_time}-{self.end_time}"