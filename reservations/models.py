"""
Reservations App Models

Handles machine reservations, training sessions/bookings, maintenance, and blackouts.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta, datetime, time


class MachineReservation(models.Model):
    """
    A student's reservation to use a specific machine.
    Rule: One reservation per machine type per student per day.
    """
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('no_show', 'No Show'),
    ]
    
    machine = models.ForeignKey(
        'machines.Machine',
        on_delete=models.CASCADE,
        related_name='reservations'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='machine_reservations'
    )
    
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    purpose = models.TextField(blank=True, help_text="What the student is working on")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['date', 'start_time']
        indexes = [
            models.Index(fields=['machine', 'date']),
            models.Index(fields=['user', 'date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.machine.name} on {self.date} {self.start_time}-{self.end_time}"
    
    def clean(self):
        """Validate the reservation"""
        errors = {}
        
        # Check times are valid
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                errors['end_time'] = "End time must be after start time"
            
            # Check max duration (24 hours)
            start_dt = datetime.combine(self.date, self.start_time)
            end_dt = datetime.combine(self.date, self.end_time)
            duration = end_dt - start_dt
            if duration > timedelta(hours=24):
                errors['end_time'] = "Reservation cannot exceed 24 hours"
            
            # Check 15-minute intervals
            if self.start_time.minute % 15 != 0:
                errors['start_time'] = "Start time must be on a 15-minute interval"
            if self.end_time.minute % 15 != 0:
                errors['end_time'] = "End time must be on a 15-minute interval"
        
        # Check date is not in the past
        if self.date and self.date < timezone.now().date():
            errors['date'] = "Cannot make reservations in the past"
        
        if errors:
            raise ValidationError(errors)
    
    @property
    def duration_minutes(self):
        """Calculate duration in minutes"""
        start_dt = datetime.combine(self.date, self.start_time)
        end_dt = datetime.combine(self.date, self.end_time)
        return int((end_dt - start_dt).total_seconds() / 60)
    
    @property
    def is_active(self):
        """Check if reservation is currently active (confirmed and not past)"""
        if self.status != 'confirmed':
            return False
        now = timezone.now()
        reservation_end = timezone.make_aware(datetime.combine(self.date, self.end_time))
        return reservation_end > now
    
    def cancel(self, reason=''):
        """Cancel this reservation"""
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.cancellation_reason = reason
        self.save()


class ReservationWaitlist(models.Model):
    """
    Waitlist for machine reservations when desired time is unavailable.
    """
    STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('notified', 'Notified'),
        ('confirmed', 'Confirmed'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]
    
    machine = models.ForeignKey(
        'machines.Machine',
        on_delete=models.CASCADE,
        related_name='waitlist_entries'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reservation_waitlist'
    )
    
    date = models.DateField()
    preferred_start_time = models.TimeField()
    preferred_end_time = models.TimeField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    
    # Notification tracking
    notified_at = models.DateTimeField(null=True, blank=True)
    confirmation_deadline = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['machine', 'date', 'status']),
        ]
    
    def __str__(self):
        return f"Waitlist: {self.user} for {self.machine.name} on {self.date}"
    
    def calculate_confirmation_deadline(self):
        """
        Calculate confirmation deadline based on how far out the reservation is.
        - If notified 5+ hours before: 3 hours to confirm
        - If notified 2+ days before: 1 day to confirm
        - Otherwise: proportional time
        """
        if not self.notified_at:
            return None
        
        reservation_datetime = timezone.make_aware(
            datetime.combine(self.date, self.preferred_start_time)
        )
        time_until = reservation_datetime - self.notified_at
        
        if time_until >= timedelta(days=2):
            return self.notified_at + timedelta(days=1)
        elif time_until >= timedelta(hours=5):
            return self.notified_at + timedelta(hours=3)
        else:
            # Give them half the remaining time
            return self.notified_at + (time_until / 2)


class TrainingSession(models.Model):
    """
    A bookable training session, auto-generated from staff Training shifts.
    Broken into slots based on training duration.
    """
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('full', 'Full'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # The trainer conducting this session
    trainer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='training_sessions_as_trainer'
    )
    
    # What training this is for
    training = models.ForeignKey(
        'machines.Training',
        on_delete=models.CASCADE,
        related_name='sessions',
        help_text="The specific training being offered"
    )
    
    # When and where
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    location = models.ForeignKey(
        'locations.Location',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='training_sessions'
    )
    
    # Capacity (from Training.max_participants)
    max_participants = models.PositiveIntegerField(default=1)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    
    # Link back to the original shift (for reference)
    source_shift = models.ForeignKey(
        'scheduling.Shift',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_training_sessions'
    )
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['date', 'start_time']
        indexes = [
            models.Index(fields=['date', 'status']),
            models.Index(fields=['trainer', 'date']),
            models.Index(fields=['training']),
        ]
    
    def __str__(self):
        return f"{self.training.name} with {self.trainer} on {self.date} {self.start_time}"
    
    @property
    def category(self):
        """Get the category from the training"""
        return self.training.category
    
    @property
    def duration_minutes(self):
        """Calculate duration in minutes"""
        start_dt = datetime.combine(self.date, self.start_time)
        end_dt = datetime.combine(self.date, self.end_time)
        return int((end_dt - start_dt).total_seconds() / 60)
    
    @property
    def current_participants(self):
        """Count of confirmed participants"""
        return self.bookings.filter(status='registered').count()
    
    @property
    def available_spots(self):
        """Number of spots still available"""
        return max(0, self.max_participants - self.current_participants)
    
    @property
    def is_full(self):
        """Check if session is at capacity"""
        return self.current_participants >= self.max_participants
    
    @property
    def waitlist_count(self):
        """Count of students on waitlist"""
        return self.bookings.filter(status='waitlisted').count()
    
    def update_status(self):
        """Update status based on capacity"""
        if self.status in ['completed', 'cancelled']:
            return
        
        if self.is_full:
            self.status = 'full'
        else:
            self.status = 'available'
        self.save()


class TrainingBooking(models.Model):
    """
    A student's registration for a training session.
    """
    STATUS_CHOICES = [
        ('registered', 'Registered'),
        ('waitlisted', 'Waitlisted'),
        ('notified', 'Notified (Waitlist)'),
        ('confirmed', 'Confirmed (from Waitlist)'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('no_show', 'No Show'),
    ]
    
    session = models.ForeignKey(
        TrainingSession,
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='training_bookings'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='registered')
    
    # Timestamps
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Waitlist notification tracking
    notified_at = models.DateTimeField(null=True, blank=True)
    confirmation_deadline = models.DateTimeField(null=True, blank=True)
    
    # Completion tracking
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trainings_marked_complete'
    )
    
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['registered_at']
        unique_together = ['session', 'user']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['session', 'status']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.session.training.name} ({self.status})"
    
    @property
    def waitlist_position(self):
        """Get position in waitlist (1-indexed), or None if not waitlisted"""
        if self.status != 'waitlisted':
            return None
        
        earlier_entries = TrainingBooking.objects.filter(
            session=self.session,
            status='waitlisted',
            registered_at__lt=self.registered_at
        ).count()
        
        return earlier_entries + 1
    
    def calculate_confirmation_deadline(self):
        """Calculate confirmation deadline for waitlist notifications"""
        if not self.notified_at:
            return None
        
        session_datetime = timezone.make_aware(
            datetime.combine(self.session.date, self.session.start_time)
        )
        time_until = session_datetime - self.notified_at
        
        if time_until >= timedelta(days=2):
            return self.notified_at + timedelta(days=1)
        elif time_until >= timedelta(hours=5):
            return self.notified_at + timedelta(hours=3)
        else:
            return self.notified_at + (time_until / 2)
    
    def mark_complete(self, completed_by_user):
        """Mark this training as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.completed_by = completed_by_user
        self.save()
        
        # Create UserTrainingRecord if it doesn't exist
        from machines.models import UserTrainingRecord
        UserTrainingRecord.objects.get_or_create(
            user=self.user,
            training=self.session.training,
            defaults={
                'status': 'completed',
                'completed_at': self.completed_at,
                'trainer': self.session.trainer,
            }
        )


class MachineMaintenance(models.Model):
    """
    Track machine maintenance issues and downtime.
    """
    STATUS_CHOICES = [
        ('reported', 'Reported'),
        ('acknowledged', 'Acknowledged'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical - Machine Offline'),
    ]
    
    machine = models.ForeignKey(
        'machines.Machine',
        on_delete=models.CASCADE,
        related_name='maintenance_logs'
    )
    
    # Issue details
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reported_maintenance'
    )
    issue_description = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='reported')
    machine_offline = models.BooleanField(
        default=False,
        help_text="If True, machine cannot be reserved"
    )
    
    # Timeline
    reported_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_maintenance'
    )
    
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_maintenance'
    )
    resolution_notes = models.TextField(blank=True)
    
    # Estimated timeline
    estimated_resolution = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Estimated time when machine will be available again"
    )
    
    class Meta:
        ordering = ['-reported_at']
        verbose_name_plural = 'Machine maintenance logs'
    
    def __str__(self):
        return f"{self.machine.name} - {self.get_status_display()} ({self.reported_at.date()})"
    
    def take_offline(self, user):
        """Take machine offline for maintenance"""
        self.machine_offline = True
        self.status = 'in_progress'
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.save()
    
    def resolve(self, user, notes=''):
        """Mark maintenance as resolved"""
        self.status = 'resolved'
        self.machine_offline = False
        self.resolved_by = user
        self.resolved_at = timezone.now()
        self.resolution_notes = notes
        self.save()


class BlackoutPeriod(models.Model):
    """
    Block reservations/bookings for specific periods.
    Can be applied globally, per location, per category, or per machine.
    """
    SCOPE_CHOICES = [
        ('global', 'All Machines'),
        ('location', 'Specific Location'),
        ('category', 'Specific Category'),
        ('machine', 'Specific Machine'),
    ]
    
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, default='global')
    
    # Optional filters (based on scope)
    location = models.ForeignKey(
        'locations.Location',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='blackout_periods'
    )
    category = models.CharField(
        max_length=50,
        blank=True,
        help_text="Machine category name"
    )
    machine = models.ForeignKey(
        'machines.Machine',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='blackout_periods'
    )
    
    # Time range
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    
    # Details
    reason = models.TextField(help_text="Reason for blackout (shown to users)")
    internal_notes = models.TextField(blank=True, help_text="Internal notes (not shown to users)")
    
    # Flags
    blocks_reservations = models.BooleanField(default=True)
    blocks_trainings = models.BooleanField(default=True)
    
    # Tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_blackouts'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_datetime']
    
    def __str__(self):
        scope_str = self.get_scope_display()
        if self.scope == 'location' and self.location:
            scope_str = f"Location: {self.location.name}"
        elif self.scope == 'category' and self.category:
            scope_str = f"Category: {self.category}"
        elif self.scope == 'machine' and self.machine:
            scope_str = f"Machine: {self.machine.name}"
        
        return f"Blackout ({scope_str}): {self.start_datetime.date()} - {self.end_datetime.date()}"
    
    def clean(self):
        if self.start_datetime and self.end_datetime:
            if self.start_datetime >= self.end_datetime:
                raise ValidationError("End time must be after start time")
        
        # Validate scope matches fields
        if self.scope == 'location' and not self.location:
            raise ValidationError("Location is required for location-scoped blackout")
        if self.scope == 'category' and not self.category:
            raise ValidationError("Category is required for category-scoped blackout")
        if self.scope == 'machine' and not self.machine:
            raise ValidationError("Machine is required for machine-scoped blackout")
    
    @classmethod
    def get_active_blackouts(cls, machine=None, category=None, location=None, at_time=None):
        """
        Get all active blackouts that apply to the given machine/category/location.
        """
        if at_time is None:
            at_time = timezone.now()
        
        blackouts = cls.objects.filter(
            start_datetime__lte=at_time,
            end_datetime__gte=at_time
        )
        
        # Filter by scope
        from django.db.models import Q
        
        scope_filter = Q(scope='global')
        
        if location:
            scope_filter |= Q(scope='location', location=location)
        
        if category:
            scope_filter |= Q(scope='category', category=category)
        
        if machine:
            scope_filter |= Q(scope='machine', machine=machine)
            # Also check machine's category and location
            if hasattr(machine, 'category'):
                scope_filter |= Q(scope='category', category=machine.category)
            if hasattr(machine, 'location'):
                scope_filter |= Q(scope='location', location=machine.location)
        
        return blackouts.filter(scope_filter)
    
    @classmethod
    def is_blocked(cls, machine, start_datetime, end_datetime, check_reservations=True, check_trainings=False):
        """
        Check if a time range is blocked for a machine.
        """
        blackouts = cls.objects.filter(
            start_datetime__lt=end_datetime,
            end_datetime__gt=start_datetime
        )
        
        # Filter by scope
        from django.db.models import Q
        
        scope_filter = Q(scope='global')
        scope_filter |= Q(scope='machine', machine=machine)
        
        if hasattr(machine, 'category'):
            scope_filter |= Q(scope='category', category=machine.category)
        if hasattr(machine, 'location'):
            scope_filter |= Q(scope='location', location=machine.location)
        
        blackouts = blackouts.filter(scope_filter)
        
        if check_reservations:
            blackouts = blackouts.filter(blocks_reservations=True)
        if check_trainings:
            blackouts = blackouts.filter(blocks_trainings=True)
        
        return blackouts.exists()