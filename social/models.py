# social/models.py
"""
Social features for The Hatchery makerspace platform.
Includes: Projects showcase, friend system, and gamification elements.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone


class Project(models.Model):
    """
    User-submitted project showcase.
    Users can share their creations and tag the machines they used.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    
    # Core fields
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='projects'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(help_text="Describe your project, process, and what you learned")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='published')
    
    # Machine tagging - stores machine IDs used in the project
    machines_used = models.ManyToManyField(
        'machines.Machine',
        blank=True,
        related_name='projects'
    )
    
    # Optional: tag machine types (for when specific machine doesn't matter)
    machine_types_used = models.JSONField(
        default=list,
        blank=True,
        help_text="List of machine type names used"
    )
    
    # Categories/tags
    categories = models.JSONField(
        default=list,
        blank=True,
        help_text="Category tags like '3D Printing', 'Laser', etc."
    )
    
    # Images
    cover_image = models.ImageField(
        upload_to='projects/covers/',
        blank=True,
        null=True
    )
    
    # Engagement
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    views_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', 'status']),
        ]
    
    def __str__(self):
        return f"{self.title} by {self.user.get_full_name() or self.user.email}"
    
    def save(self, *args, **kwargs):
        # Set published_at when first published
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)
    
    @property
    def author_name(self):
        return self.user.get_full_name() or self.user.email.split('@')[0]


class ProjectImage(models.Model):
    """Additional images for a project (gallery)."""
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='projects/gallery/')
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return f"Image for {self.project.title}"


class ProjectLike(models.Model):
    """Track who liked which projects."""
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='likes'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_likes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['project', 'user']
    
    def __str__(self):
        return f"{self.user} likes {self.project.title}"


class ProjectComment(models.Model):
    """Comments on projects."""
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_comments'
    )
    content = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # For threaded comments (optional)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.user} on {self.project.title}"


class Friendship(models.Model):
    """
    Friend relationships between users.
    Uses a single record per friendship (user1 < user2 by ID to avoid duplicates).
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('blocked', 'Blocked'),
    ]
    
    # The user who sent the request
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='friendships_sent'
    )
    # The user who received the request
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='friendships_received'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['from_user', 'to_user']
        indexes = [
            models.Index(fields=['from_user', 'status']),
            models.Index(fields=['to_user', 'status']),
        ]
    
    def __str__(self):
        return f"{self.from_user} → {self.to_user} ({self.status})"
    
    def accept(self):
        self.status = 'accepted'
        self.accepted_at = timezone.now()
        self.save()
    
    def decline(self):
        self.status = 'declined'
        self.save()


class UserStats(models.Model):
    """
    Cached statistics for gamification.
    Updated via signals when relevant actions occur.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stats'
    )
    
    # Projects
    projects_count = models.PositiveIntegerField(default=0)
    total_likes_received = models.PositiveIntegerField(default=0)
    
    # Training & Certifications
    trainings_completed = models.PositiveIntegerField(default=0)
    certifications_count = models.PositiveIntegerField(default=0)
    
    # Machine usage
    unique_machines_used = models.PositiveIntegerField(default=0)
    total_reservations = models.PositiveIntegerField(default=0)
    total_hours_logged = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Social
    friends_count = models.PositiveIntegerField(default=0)
    
    # Achievements/badges stored as JSON
    badges = models.JSONField(default=list, blank=True)
    
    # Level/XP for gamification
    xp_points = models.PositiveIntegerField(default=0)
    level = models.PositiveIntegerField(default=1)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Stats for {self.user}"
    
    def calculate_level(self):
        """Calculate level based on XP (simple formula)."""
        # Level up every 100 XP
        self.level = (self.xp_points // 100) + 1
        return self.level
    
    def add_xp(self, points, reason=None):
        """Add XP points and recalculate level."""
        self.xp_points += points
        self.calculate_level()
        self.save()
        return self.xp_points
    
    @classmethod
    def get_or_create_for_user(cls, user):
        """Get or create stats for a user."""
        stats, created = cls.objects.get_or_create(user=user)
        return stats


class Badge(models.Model):
    """
    Achievement badges that users can earn.
    """
    CATEGORY_CHOICES = [
        ('training', 'Training'),
        ('projects', 'Projects'),
        ('social', 'Social'),
        ('machines', 'Machines'),
        ('special', 'Special'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=10, default='🏆')  # Emoji or icon class
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    
    # Requirements (stored as JSON for flexibility)
    requirements = models.JSONField(
        default=dict,
        help_text="JSON object describing requirements, e.g., {'trainings_completed': 5}"
    )
    
    # XP reward for earning this badge
    xp_reward = models.PositiveIntegerField(default=50)
    
    # Rarity for display purposes
    RARITY_CHOICES = [
        ('common', 'Common'),
        ('uncommon', 'Uncommon'),
        ('rare', 'Rare'),
        ('epic', 'Epic'),
        ('legendary', 'Legendary'),
    ]
    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES, default='common')
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.icon} {self.name}"


class UserBadge(models.Model):
    """Track which badges users have earned."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='earned_badges'
    )
    badge = models.ForeignKey(
        Badge,
        on_delete=models.CASCADE,
        related_name='earned_by'
    )
    earned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'badge']
        ordering = ['-earned_at']
    
    def __str__(self):
        return f"{self.user} earned {self.badge.name}"