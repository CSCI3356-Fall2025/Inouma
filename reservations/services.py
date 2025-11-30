"""
Reservation Services

Business logic for validating and creating reservations.
"""

from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta, time
from typing import Optional, Tuple, List, Dict, Any


class ReservationValidationError(Exception):
    """Custom exception for reservation validation errors"""
    def __init__(self, message, code=None):
        self.message = message
        self.code = code
        super().__init__(message)


class ReservationService:
    """
    Service class for machine reservation operations.
    """
    
    # Time slot settings
    SLOT_INTERVAL_MINUTES = 15
    MAX_DURATION_HOURS = 24
    
    @classmethod
    def validate_reservation(
        cls,
        machine,
        user,
        date,
        start_time,
        end_time,
        exclude_reservation_id=None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a reservation request.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        from .models import MachineReservation, BlackoutPeriod, MachineMaintenance
        
        # 1. Check times are valid
        if start_time >= end_time:
            return False, "End time must be after start time"
        
        # 2. Check 15-minute intervals
        if start_time.minute % cls.SLOT_INTERVAL_MINUTES != 0:
            return False, f"Start time must be on a {cls.SLOT_INTERVAL_MINUTES}-minute interval"
        if end_time.minute % cls.SLOT_INTERVAL_MINUTES != 0:
            return False, f"End time must be on a {cls.SLOT_INTERVAL_MINUTES}-minute interval"
        
        # 3. Check max duration
        start_dt = datetime.combine(date, start_time)
        end_dt = datetime.combine(date, end_time)
        duration = end_dt - start_dt
        if duration > timedelta(hours=cls.MAX_DURATION_HOURS):
            return False, f"Reservation cannot exceed {cls.MAX_DURATION_HOURS} hours"
        
        # 4. Check date is not in the past
        now = timezone.now()
        if date < now.date():
            return False, "Cannot make reservations in the past"
        if date == now.date() and start_time < now.time():
            return False, "Cannot make reservations for past times"
        
        # 5. Check user has required training
        is_trained, missing_trainings = cls.check_user_training(machine, user)
        if not is_trained:
            training_names = ", ".join(missing_trainings)
            return False, f"Required training not completed: {training_names}"
        
        # 6. Check one reservation per machine type per day rule
        existing_same_type = MachineReservation.objects.filter(
            user=user,
            date=date,
            machine__machine_name=machine.machine_name,
            status='confirmed'
        )
        if exclude_reservation_id:
            existing_same_type = existing_same_type.exclude(id=exclude_reservation_id)
        
        if existing_same_type.exists():
            return False, f"You already have a reservation for a {machine.machine_name} on this date"
        
        # 7. Check machine is not in maintenance
        active_maintenance = MachineMaintenance.objects.filter(
            machine=machine,
            machine_offline=True,
            status__in=['reported', 'acknowledged', 'in_progress']
        ).first()
        
        if active_maintenance:
            return False, f"Machine is currently offline for maintenance: {active_maintenance.issue_description[:100]}"
        
        # 8. Check for blackout periods
        start_datetime = timezone.make_aware(datetime.combine(date, start_time))
        end_datetime = timezone.make_aware(datetime.combine(date, end_time))
        
        if BlackoutPeriod.is_blocked(machine, start_datetime, end_datetime, check_reservations=True):
            blackout = BlackoutPeriod.get_active_blackouts(
                machine=machine, 
                at_time=start_datetime
            ).first()
            reason = blackout.reason if blackout else "Reservations blocked during this time"
            return False, f"Reservations not available: {reason}"
        
        # 9. Check for conflicts with existing reservations
        conflicts = MachineReservation.objects.filter(
            machine=machine,
            date=date,
            status='confirmed'
        ).filter(
            Q(start_time__lt=end_time) & Q(end_time__gt=start_time)
        )
        
        if exclude_reservation_id:
            conflicts = conflicts.exclude(id=exclude_reservation_id)
        
        if conflicts.exists():
            return False, "This time slot conflicts with an existing reservation"
        
        return True, None
    
    @classmethod
    def check_user_training(cls, machine, user) -> Tuple[bool, List[str]]:
        """
        Check if user has completed required training for this machine.
        
        Returns:
            Tuple of (is_trained, list_of_missing_training_names)
        """
        from machines.models import UserTrainingRecord, Training
        
        # Get required trainings for this machine type
        required_trainings = Training.objects.filter(
            status='active',
            machine_type_names__contains=machine.machine_name
        )
        
        if not required_trainings.exists():
            # No training required
            return True, []
        
        # Check which trainings the user has completed
        completed_training_ids = UserTrainingRecord.objects.filter(
            user=user,
            status='completed'
        ).values_list('training_id', flat=True)
        
        missing = []
        for training in required_trainings:
            if training.id not in completed_training_ids:
                missing.append(training.name)
        
        return len(missing) == 0, missing
    
    @classmethod
    def create_reservation(
        cls,
        machine,
        user,
        date,
        start_time,
        end_time,
        purpose=''
    ):
        """
        Create a new machine reservation after validation.
        
        Returns:
            MachineReservation instance
            
        Raises:
            ReservationValidationError if validation fails
        """
        from .models import MachineReservation
        
        # Validate first
        is_valid, error = cls.validate_reservation(
            machine, user, date, start_time, end_time
        )
        
        if not is_valid:
            raise ReservationValidationError(error)
        
        # Create reservation
        reservation = MachineReservation.objects.create(
            machine=machine,
            user=user,
            date=date,
            start_time=start_time,
            end_time=end_time,
            purpose=purpose,
            status='confirmed'
        )
        
        return reservation
    
    @classmethod
    def get_available_slots(
        cls,
        machine,
        date,
        min_duration_minutes=15
    ) -> List[Dict[str, Any]]:
        """
        Get available time slots for a machine on a given date.
        
        Returns:
            List of dicts with 'start_time', 'end_time', 'duration_minutes'
        """
        from .models import MachineReservation, BlackoutPeriod, MachineMaintenance
        
        # Check if machine is in maintenance
        if MachineMaintenance.objects.filter(
            machine=machine,
            machine_offline=True,
            status__in=['reported', 'acknowledged', 'in_progress']
        ).exists():
            return []
        
        # Define operating hours (TODO: make configurable per location)
        operating_start = time(8, 0)  # 8 AM
        operating_end = time(22, 0)   # 10 PM
        
        # Get existing reservations for this date
        reservations = MachineReservation.objects.filter(
            machine=machine,
            date=date,
            status='confirmed'
        ).order_by('start_time')
        
        # Build list of blocked periods
        blocked = []
        
        # Add reservations to blocked list
        for r in reservations:
            blocked.append((r.start_time, r.end_time))
        
        # Add blackout periods
        day_start = timezone.make_aware(datetime.combine(date, operating_start))
        day_end = timezone.make_aware(datetime.combine(date, operating_end))
        
        blackouts = BlackoutPeriod.objects.filter(
            start_datetime__lt=day_end,
            end_datetime__gt=day_start,
            blocks_reservations=True
        )
        
        # Filter blackouts that apply to this machine
        for b in blackouts:
            applies = False
            if b.scope == 'global':
                applies = True
            elif b.scope == 'machine' and b.machine_id == machine.id:
                applies = True
            elif b.scope == 'category' and b.category == machine.category:
                applies = True
            elif b.scope == 'location' and b.location_id == machine.location_id:
                applies = True
            
            if applies:
                # Convert blackout times to time objects for this date
                b_start = max(b.start_datetime.time(), operating_start) if b.start_datetime.date() <= date else operating_start
                b_end = min(b.end_datetime.time(), operating_end) if b.end_datetime.date() >= date else operating_end
                
                if b.start_datetime.date() < date:
                    b_start = operating_start
                if b.end_datetime.date() > date:
                    b_end = operating_end
                
                blocked.append((b_start, b_end))
        
        # Sort and merge overlapping blocked periods
        blocked.sort(key=lambda x: x[0])
        merged = []
        for start, end in blocked:
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        
        # Find available slots
        available = []
        current = operating_start
        
        for block_start, block_end in merged:
            if current < block_start:
                # There's an available slot before this block
                slot_duration = (
                    datetime.combine(date, block_start) - 
                    datetime.combine(date, current)
                ).total_seconds() / 60
                
                if slot_duration >= min_duration_minutes:
                    available.append({
                        'start_time': current.strftime('%H:%M'),
                        'end_time': block_start.strftime('%H:%M'),
                        'duration_minutes': int(slot_duration)
                    })
            
            current = max(current, block_end)
        
        # Check for slot after last block
        if current < operating_end:
            slot_duration = (
                datetime.combine(date, operating_end) - 
                datetime.combine(date, current)
            ).total_seconds() / 60
            
            if slot_duration >= min_duration_minutes:
                available.append({
                    'start_time': current.strftime('%H:%M'),
                    'end_time': operating_end.strftime('%H:%M'),
                    'duration_minutes': int(slot_duration)
                })
        
        # If today, filter out past slots
        if date == timezone.now().date():
            now = timezone.now().time()
            available = [
                slot for slot in available 
                if datetime.strptime(slot['end_time'], '%H:%M').time() > now
            ]
        
        return available
    
    @classmethod
    def cancel_reservation(cls, reservation, user, reason=''):
        """
        Cancel a reservation.
        """
        from .models import ReservationWaitlist
        
        reservation.cancel(reason)
        
        # Check waitlist and notify next person
        waitlist_entry = ReservationWaitlist.objects.filter(
            machine=reservation.machine,
            date=reservation.date,
            status='waiting',
            preferred_start_time__lte=reservation.start_time,
            preferred_end_time__gte=reservation.end_time
        ).order_by('created_at').first()
        
        if waitlist_entry:
            cls.notify_waitlist_entry(waitlist_entry)
        
        return True
    
    @classmethod
    def notify_waitlist_entry(cls, entry):
        """
        Notify a waitlist entry that a slot is available.
        """
        entry.status = 'notified'
        entry.notified_at = timezone.now()
        entry.confirmation_deadline = entry.calculate_confirmation_deadline()
        entry.save()
        
        # TODO: Send email notification
        # send_waitlist_notification_email(entry)


class TrainingSessionService:
    """
    Service class for training session operations.
    """
    
    @classmethod
    def generate_sessions_from_shift(cls, shift):
        """
        Generate TrainingSession objects from a training shift.
        Breaks the shift into slots based on training duration.
        
        Args:
            shift: Shift object with shift_type='training'
        """
        from .models import TrainingSession
        from machines.models import Training
        from team.models import TeamMember
        
        if shift.shift_type != 'training':
            return []
        
        # Get the team member's certified categories
        try:
            team_member = TeamMember.objects.get(user=shift.user)
            certified_categories = list(team_member.categories.values_list('name', flat=True))
        except TeamMember.DoesNotExist:
            # Fall back to team_category from the shift itself
            certified_categories = [shift.team_category] if shift.team_category else []
        
        if not certified_categories:
            return []
        
        sessions_created = []
        shift_start = datetime.combine(shift.date, shift.start_time)
        shift_end = datetime.combine(shift.date, shift.end_time)
        
        # For each certified category, get the trainings and create sessions
        for category in certified_categories:
            trainings = Training.objects.filter(
                category=category,
                status='active'
            ).order_by('level')
            
            for training in trainings:
                # Calculate how many sessions fit in the shift
                training_duration = timedelta(minutes=training.duration_minutes)
                
                current_start = shift_start
                while current_start + training_duration <= shift_end:
                    current_end = current_start + training_duration
                    
                    # Check if session already exists
                    existing = TrainingSession.objects.filter(
                        trainer=shift.user,
                        training=training,
                        date=shift.date,
                        start_time=current_start.time()
                    ).exists()
                    
                    if not existing:
                        session = TrainingSession.objects.create(
                            trainer=shift.user,
                            training=training,
                            date=shift.date,
                            start_time=current_start.time(),
                            end_time=current_end.time(),
                            max_participants=training.max_participants,
                            source_shift=shift,
                            status='available'
                        )
                        sessions_created.append(session)
                    
                    current_start = current_end
        
        return sessions_created
    
    @classmethod
    def generate_sessions_for_semester(cls, semester):
        """
        Generate all training sessions for a published semester schedule.
        """
        from scheduling.models import Shift
        
        # Get all training shifts for the semester
        training_shifts = Shift.objects.filter(
            semester=semester,
            shift_type='training',
            status='scheduled'
        )
        
        all_sessions = []
        for shift in training_shifts:
            sessions = cls.generate_sessions_from_shift(shift)
            all_sessions.extend(sessions)
        
        return all_sessions
    
    @classmethod
    def book_training(cls, session, user):
        """
        Book a user into a training session.
        
        Returns:
            TrainingBooking instance
            
        Raises:
            ReservationValidationError if booking fails
        """
        from .models import TrainingBooking
        from machines.models import UserTrainingRecord
        
        # Check if user already completed this training
        already_completed = UserTrainingRecord.objects.filter(
            user=user,
            training=session.training,
            status='completed'
        ).exists()
        
        if already_completed:
            raise ReservationValidationError(
                "You have already completed this training",
                code='already_trained'
            )
        
        # Check if user already has a booking for this session
        existing_booking = TrainingBooking.objects.filter(
            session=session,
            user=user
        ).exclude(status__in=['cancelled', 'no_show']).first()
        
        if existing_booking:
            raise ReservationValidationError(
                f"You are already {existing_booking.get_status_display().lower()} for this session",
                code='already_booked'
            )
        
        # Check if session is in the past
        session_datetime = timezone.make_aware(
            datetime.combine(session.date, session.start_time)
        )
        if session_datetime < timezone.now():
            raise ReservationValidationError(
                "Cannot book past sessions",
                code='past_session'
            )
        
        # Check session status
        if session.status == 'cancelled':
            raise ReservationValidationError(
                "This session has been cancelled",
                code='session_cancelled'
            )
        
        # Determine booking status based on capacity
        if session.is_full:
            status = 'waitlisted'
        else:
            status = 'registered'
        
        # Create booking
        booking = TrainingBooking.objects.create(
            session=session,
            user=user,
            status=status
        )
        
        # Update session status
        session.update_status()
        
        return booking
    
    @classmethod
    def cancel_booking(cls, booking, notify_waitlist=True):
        """
        Cancel a training booking.
        """
        from .models import TrainingBooking
        
        was_registered = booking.status == 'registered'
        booking.status = 'cancelled'
        booking.save()
        
        # Update session status
        booking.session.update_status()
        
        # If was registered and there's a waitlist, notify next person
        if was_registered and notify_waitlist:
            next_waitlisted = TrainingBooking.objects.filter(
                session=booking.session,
                status='waitlisted'
            ).order_by('registered_at').first()
            
            if next_waitlisted:
                cls.notify_waitlisted_booking(next_waitlisted)
        
        return True
    
    @classmethod
    def notify_waitlisted_booking(cls, booking):
        """
        Notify a waitlisted booking that a spot is available.
        """
        booking.status = 'notified'
        booking.notified_at = timezone.now()
        booking.confirmation_deadline = booking.calculate_confirmation_deadline()
        booking.save()
        
        # TODO: Send email notification
        # send_training_waitlist_notification_email(booking)
    
    @classmethod
    def confirm_waitlist_booking(cls, booking):
        """
        Confirm a notified waitlist booking.
        """
        if booking.status != 'notified':
            raise ReservationValidationError(
                "Booking is not in notified status",
                code='invalid_status'
            )
        
        if booking.confirmation_deadline and timezone.now() > booking.confirmation_deadline:
            raise ReservationValidationError(
                "Confirmation deadline has passed",
                code='deadline_passed'
            )
        
        booking.status = 'confirmed'
        booking.save()
        
        booking.session.update_status()
        
        return booking
    
    @classmethod
    def get_available_sessions(
        cls,
        category=None,
        training=None,
        start_date=None,
        end_date=None,
        user=None
    ):
        """
        Get available training sessions, optionally filtered.
        """
        from .models import TrainingSession
        from machines.models import UserTrainingRecord
        
        if start_date is None:
            start_date = timezone.now().date()
        if end_date is None:
            end_date = start_date + timedelta(days=14)  # 2 weeks ahead
        
        sessions = TrainingSession.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            status__in=['available', 'full']  # Include full for waitlist
        ).select_related('training', 'trainer', 'location')
        
        if category:
            sessions = sessions.filter(training__category=category)
        
        if training:
            sessions = sessions.filter(training=training)
        
        # If user provided, exclude trainings they've already completed
        if user:
            completed_training_ids = UserTrainingRecord.objects.filter(
                user=user,
                status='completed'
            ).values_list('training_id', flat=True)
            
            sessions = sessions.exclude(training_id__in=completed_training_ids)
        
        return sessions.order_by('date', 'start_time')