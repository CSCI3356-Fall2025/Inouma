"""
Reservations App Signals

Auto-generate training sessions when schedules are published.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver


def generate_training_sessions_for_schedule(semester):
    """
    Generate training sessions for all training shifts in a published semester.
    Called when a semester schedule is published.
    """
    from .services import TrainingSessionService
    
    sessions = TrainingSessionService.generate_sessions_for_semester(semester)
    return len(sessions)


# Alternative: Use a management command or call manually after publishing
# This avoids circular imports and gives more control

def connect_schedule_signals():
    """
    Connect to schedule publishing signals.
    Call this from the app's ready() method if using signals.
    """
    try:
        from scheduling.models import Semester
        
        @receiver(post_save, sender=Semester)
        def on_semester_save(sender, instance, **kwargs):
            # Only generate sessions when schedule is published
            if instance.schedule_published and not kwargs.get('raw', False):
                # Check if sessions already exist for this semester
                from .models import TrainingSession
                existing = TrainingSession.objects.filter(
                    source_shift__semester=instance
                ).exists()
                
                if not existing:
                    from .services import TrainingSessionService
                    TrainingSessionService.generate_sessions_for_semester(instance)
    
    except ImportError:
        pass


# Utility function to regenerate sessions
def regenerate_training_sessions(semester, force=False):
    """
    Regenerate training sessions for a semester.
    
    Args:
        semester: Semester instance
        force: If True, delete existing sessions first
    """
    from .models import TrainingSession
    from .services import TrainingSessionService
    
    if force:
        # Delete existing sessions (only future ones without bookings)
        from django.utils import timezone
        TrainingSession.objects.filter(
            source_shift__semester=semester,
            date__gte=timezone.now().date(),
            bookings__isnull=True
        ).delete()
    
    sessions = TrainingSessionService.generate_sessions_for_semester(semester)
    return len(sessions)