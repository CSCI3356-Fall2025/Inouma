from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from locations.models import Location


# ============================================
# SEMESTER & OPERATING HOURS
# ============================================

class Semester(models.Model):
    """Represents an academic semester with operating hours"""
    
    SEMESTER_CHOICES = [
        ('fall', 'Fall'),
        ('spring', 'Spring'),
        ('summer', 'Summer'),
    ]
    
    name = models.CharField(max_length=100, help_text="e.g., 'Fall 2025'")
    semester_type = models.CharField(max_length=10, choices=SEMESTER_CHOICES)
    year = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    holidays = models.JSONField(
        default=list, 
        blank=True,
        help_text="List of holiday dates in ISO format ['2025-11-28', '2025-12-25']"
    )
    is_active = models.BooleanField(default=False, help_text="Only one semester can be active at a time")
    is_archived = models.BooleanField(default=False, help_text="Archived semesters are hidden from normal view")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_date']
        unique_together = ['semester_type', 'year']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Ensure only one active semester
        if self.is_active:
            Semester.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class DailyOperatingHours(models.Model):
    """Operating hours for each day of the week in a semester"""
    
    WEEKDAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='operating_hours')
    day_of_week = models.IntegerField(choices=WEEKDAY_CHOICES)
    
    is_closed = models.BooleanField(default=False, help_text="Is the space closed this day?")
    training_disabled = models.BooleanField(default=False, help_text="Disable training on this day (even if closed)")
    
    # Open hours (when students can book time with hosts)
    open_hours_start = models.TimeField(null=True, blank=True, help_text="When open hours hosting begins")
    open_hours_end = models.TimeField(null=True, blank=True, help_text="When open hours hosting ends")
    
    # Training availability (when trainers can be scheduled)
    training_start = models.TimeField(null=True, blank=True, help_text="When training sessions can be scheduled")
    training_end = models.TimeField(null=True, blank=True, help_text="When training sessions end")
    
    class Meta:
        ordering = ['semester', 'day_of_week']
        unique_together = ['semester', 'day_of_week']
        verbose_name_plural = 'Daily Operating Hours'
    
    def __str__(self):
        return f"{self.semester.name} - {self.get_day_of_week_display()}"
    
    def clean(self):
        if not self.is_closed:
            # If open hours are specified, validate them
            if self.open_hours_start and self.open_hours_end:
                if self.open_hours_end <= self.open_hours_start:
                    raise ValidationError("Open hours end must be after start")
            
            # If training hours are specified, validate them
            if self.training_start and self.training_end:
                if self.training_end <= self.training_start:
                    raise ValidationError("Training end must be after start")
        else:
            # If closed, can't have open hours (but can have training)
            if self.open_hours_start or self.open_hours_end:
                raise ValidationError("Cannot set open hours on a closed day")


# ============================================
# LOCATION GROUPING
# ============================================

class LocationGroup(models.Model):
    """Group multiple locations to be hosted by a single person"""
    
    name = models.CharField(max_length=200, help_text="e.g., 'Woodshop Combined'")
    locations = models.ManyToManyField(Location, related_name='groups')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_location_names(self):
        return ", ".join([loc.name for loc in self.locations.all()])


# ============================================
# SHIFT REQUIREMENTS
# ============================================

class ShiftRequirement(models.Model):
    """Defines how many hosts/floaters are needed for a given time/location"""
    
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='shift_requirements')
    day_of_week = models.IntegerField(choices=DailyOperatingHours.WEEKDAY_CHOICES)
    time_start = models.TimeField()
    time_end = models.TimeField()
    
    # What needs to be covered
    location = models.ForeignKey(
        Location, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="Individual location needing hosts"
    )
    location_group = models.ForeignKey(
        LocationGroup, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="Or a group of locations needing hosts"
    )
    
    # Requirements (non-negative)
    hosts_required = models.PositiveIntegerField(
        default=0, 
        help_text="Number of hosts needed for this location/group"
    )
    floaters_required = models.PositiveIntegerField(
        default=0, 
        help_text="Number of floaters needed (not location-specific)"
    )
    
    # For varying requirements during peak hours
    is_peak_hours = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['semester', 'day_of_week', 'time_start']
        # Prevent duplicates
        unique_together = ['semester', 'day_of_week', 'time_start', 'time_end', 'location', 'location_group']
    
    def __str__(self):
        target = self.location.name if self.location else (self.location_group.name if self.location_group else "General")
        return f"{self.semester.name} - {self.get_day_of_week_display()} {self.time_start}-{self.time_end} @ {target}"
    
    def clean(self):
        # Must specify either location OR location_group (not both) if hosts are required
        if self.location and self.location_group:
            raise ValidationError("Specify either location OR location_group, not both")
        
        if self.hosts_required > 0 and not self.location and not self.location_group:
            raise ValidationError("Must specify location or location_group if hosts are required")
        
        if self.time_end <= self.time_start:
            raise ValidationError("End time must be after start time")
        
        # Must have at least one requirement
        if self.hosts_required == 0 and self.floaters_required == 0:
            raise ValidationError("Must specify at least one host or floater requirement")


# ============================================
# USER EXTENSIONS (Team, Preferences)
# ============================================

# ============================================
# TEAM GROUPS
# ============================================

class TeamGroup(models.Model):
    """Groups/teams within the Hatchery"""
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#6b7280', help_text="Hex color for UI display")
    lead = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='led_groups'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class TeamMemberProfile(models.Model):
    """Extended profile for team members with scheduling info"""
    
    ROLE_CHOICES = [
        ('team_member', 'Team Member'),
        ('team_lead', 'Team Lead'),
        ('floater', 'Floater'),
        ('staff', 'Staff'),
    ]
    
    SHIFT_PREFERENCE_CHOICES = [
        ('few_long', 'Few Long Shifts'),
        ('many_short', 'Many Short Shifts'),
        ('no_preference', 'No Preference'),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='team_profile'
    )
    
    # Optional semester association
    semester = models.ForeignKey(
        Semester,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='team_members'
    )
    
    # Team group assignment
    team_group = models.ForeignKey(
        TeamGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members'
    )
    
    # Legacy team assignment (based on machine categories)
    team = models.CharField(
        max_length=50, 
        blank=True, 
        help_text="Machine category: Laser, 3D Printing, Woodworking, etc."
    )
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='team_member')
    
    # Personal info
    phone = models.CharField(max_length=20, blank=True)
    birthday = models.DateField(null=True, blank=True)
    graduation_year = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True, help_text="Admin notes about this team member")
    profile_image_url = models.URLField(blank=True, help_text="URL to profile image")
    
    # Scheduling preferences
    min_weekly_hours = models.IntegerField(
        default=0,
        help_text="Minimum hours per week"
    )
    max_weekly_hours = models.IntegerField(
        default=15,
        help_text="Maximum hours per week"
    )
    expected_weekly_hours = models.IntegerField(
        default=10, 
        help_text="Expected hours per week to work (deprecated, use max)"
    )
    shift_preference = models.CharField(
        max_length=20, 
        choices=SHIFT_PREFERENCE_CHOICES, 
        default='no_preference'
    )
    
    # Role flags
    is_trainer = models.BooleanField(
        default=False,
        help_text="Can this member conduct training sessions?"
    )
    is_team_lead = models.BooleanField(
        default=False,
        help_text="Is this member a team lead?"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive members won't be scheduled"
    )
    
    # Can override per semester
    semester_overrides = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Semester-specific hours: {'fall2025': 15, 'spring2026': 8}"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['user__last_name', 'user__first_name']
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.email} - {self.get_role_display()}"
    
    def get_expected_hours(self, semester=None):
        """Get expected hours for a specific semester or default"""
        if semester and semester.name in self.semester_overrides:
            return self.semester_overrides[semester.name]
        return self.max_weekly_hours


class Unavailability(models.Model):
    """When a team member is unavailable during the week"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='unavailabilities'
    )
    semester = models.ForeignKey(
        Semester, 
        on_delete=models.CASCADE, 
        related_name='unavailabilities',
        null=True,
        blank=True
    )
    
    day_of_week = models.IntegerField(choices=DailyOperatingHours.WEEKDAY_CHOICES)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    
    is_unavailable = models.BooleanField(
        default=False,
        help_text="If true, user is unavailable. If false, times indicate availability."
    )
    
    reason = models.CharField(max_length=200, blank=True, help_text="Optional reason")
    
    class Meta:
        ordering = ['user', 'day_of_week', 'start_time']
        verbose_name_plural = 'Unavailabilities'
        unique_together = ['user', 'semester', 'day_of_week']
    
    def __str__(self):
        status = "Unavailable" if self.is_unavailable else "Available"
        time_range = f"{self.start_time}-{self.end_time}" if self.start_time and self.end_time else "All day"
        return f"{self.user.get_full_name()} - {self.get_day_of_week_display()} {time_range} ({status})"


# ============================================
# SHIFTS (Scheduled Work)
# ============================================

class Shift(models.Model):
    """A scheduled work shift for a team member"""
    
    SHIFT_TYPE_CHOICES = [
        ('open_hours', 'Open Hours Hosting'),
        ('training', 'Training Available'),
        ('floater', 'Floater'),
    ]
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('cancelled', 'Cancelled'),
        ('swap_requested', 'Swap Requested'),
        ('swap_approved', 'Swap Approved'),
        ('amendment_requested', 'Amendment Requested'),
        ('amendment_approved', 'Amendment Approved'),
    ]
    
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='shifts')
    
    # Who and when
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='shifts'
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    # What type of shift
    shift_type = models.CharField(max_length=20, choices=SHIFT_TYPE_CHOICES)
    
    # For open hours: which location/group
    location = models.ForeignKey(
        Location, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='shifts'
    )
    location_group = models.ForeignKey(
        LocationGroup, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='shifts'
    )
    
    # For training: which team/category
    team_category = models.CharField(
        max_length=50, 
        blank=True,
        null=True,  # Allow null for non-training shifts
        help_text="Machine category for training availability"
    )
    
    # Status tracking
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='scheduled')
    
    # For swaps and amendments
    original_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='swapped_shifts',
        help_text="Original user before swap"
    )
    swap_requested_with = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='swap_requests_received',
        help_text="User requested to swap with"
    )
    
    # For cancellations
    cancellation_reason = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Approval tracking
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_shifts'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['date', 'start_time']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.date} {self.start_time}-{self.end_time} ({self.get_shift_type_display()})"
    
    def clean(self):
        if self.end_time <= self.start_time:
            raise ValidationError("End time must be after start time")
        
        # Open hours must have location or location_group
        if self.shift_type == 'open_hours' and not self.location and not self.location_group:
            raise ValidationError("Open hours shifts must have a location or location_group")
        
        # Training must have team_category
        if self.shift_type == 'training' and not self.team_category:
            raise ValidationError("Training shifts must have a team_category")
    
    def duration_hours(self):
        """Calculate shift duration in hours"""
        from datetime import datetime, timedelta
        start = datetime.combine(self.date, self.start_time)
        end = datetime.combine(self.date, self.end_time)
        duration = end - start
        return duration.total_seconds() / 3600


# ============================================
# SCHEDULE PUBLICATION
# ============================================

class SchedulePublication(models.Model):
    """Track when schedules are published to users"""
    
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('partial', 'Partial'),
        ('failed', 'Failed'),
    ]
    
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='publications')
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True
    )
    published_at = models.DateTimeField(auto_now_add=True)
    
    # Publication details
    weeks_count = models.IntegerField(default=0)
    recipients_count = models.IntegerField(default=0)
    
    # What was sent
    calendar_invites_sent = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-published_at']
    
    def __str__(self):
        return f"{self.semester.name} - Published {self.published_at.strftime('%Y-%m-%d %H:%M')}"


# ============================================
# SWAP/AMENDMENT REQUESTS
# ============================================

class ShiftChangeRequest(models.Model):
    """Requests for shift swaps, amendments, or cancellations"""
    
    REQUEST_TYPE_CHOICES = [
        ('swap', 'Shift Swap'),
        ('amendment', 'Amendment'),
        ('cancellation', 'Cancellation'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('auto_approved', 'Auto-Approved'),  # For swaps when both parties agree
    ]
    
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name='change_requests')
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='shift_change_requests'
    )
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPE_CHOICES)
    
    # For swaps
    swap_with_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='swap_offers_received'
    )
    swap_with_shift = models.ForeignKey(
        Shift, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='swap_targets'
    )
    swap_accepted_by_other_user = models.BooleanField(default=False)
    
    # For amendments
    proposed_date = models.DateField(null=True, blank=True)
    proposed_start_time = models.TimeField(null=True, blank=True)
    proposed_end_time = models.TimeField(null=True, blank=True)
    
    # For cancellations
    cancellation_reason = models.TextField(blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reviewed_requests'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_request_type_display()} - {self.requested_by.get_full_name()} ({self.status})"