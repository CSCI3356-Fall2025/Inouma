"""
Reservations API Views

API endpoints for machine reservations and training bookings.
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta, date
import json

from .models import (
    MachineReservation, 
    ReservationWaitlist,
    TrainingSession, 
    TrainingBooking,
    MachineMaintenance,
    BlackoutPeriod
)
from .services import (
    ReservationService, 
    ReservationValidationError,
    TrainingSessionService
)

User = get_user_model()


def is_staff_or_admin(user):
    return user.is_staff or user.is_superuser


def is_team_member(user):
    # Consider role/flags on the User model and scheduling profile
    if getattr(user, 'role', '') == 'Team Member':
        return True
    if getattr(user, 'is_trainer', False) or getattr(user, 'is_team_lead', False):
        return True
    if user.is_staff:
        return True
    # Fallback: check scheduling profile if it exists
    try:
        profile = getattr(user, 'team_profile', None)
        if profile and (profile.is_trainer or profile.is_team_lead):
            return True
    except Exception:
        pass
    return False


# ============================================================================
# MACHINE RESERVATION APIs
# ============================================================================

@login_required
def api_check_availability(request, machine_id):
    """Check available time slots for a machine on a given date."""
    from machines.models import Machine
    
    machine = get_object_or_404(Machine, id=machine_id)
    date_str = request.GET.get('date')
    
    if not date_str:
        return JsonResponse({'success': False, 'error': 'Date is required'})
    
    try:
        check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid date format'})
    
    available_slots = ReservationService.get_available_slots(machine, check_date)
    
    # Check user's training status
    is_trained, missing = ReservationService.check_user_training(machine, request.user)
    
    return JsonResponse({
        'success': True,
        'date': date_str,
        'machine_id': machine_id,
        'machine_name': machine.name,
        'available_slots': available_slots,
        'is_trained': is_trained,
        'missing_trainings': missing,
    })


@login_required
@require_POST
def api_create_reservation(request, machine_id):
    """Create a new machine reservation."""
    from machines.models import Machine
    
    machine = get_object_or_404(Machine, id=machine_id)
    
    try:
        # Parse form data or JSON
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        date_str = data.get('reservation_date') or data.get('date')
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        purpose = data.get('purpose', '')
        
        if not all([date_str, start_time_str, end_time_str]):
            return JsonResponse({
                'success': False, 
                'error': 'Date, start time, and end time are required'
            })
        
        # Parse date and times
        reservation_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Create reservation
        reservation = ReservationService.create_reservation(
            machine=machine,
            user=request.user,
            date=reservation_date,
            start_time=start_time,
            end_time=end_time,
            purpose=purpose
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Reservation created successfully',
            'reservation': {
                'id': reservation.id,
                'machine': machine.name,
                'date': str(reservation.date),
                'start_time': reservation.start_time.strftime('%H:%M'),
                'end_time': reservation.end_time.strftime('%H:%M'),
                'status': reservation.status,
            }
        })
        
    except ReservationValidationError as e:
        return JsonResponse({'success': False, 'error': e.message})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def api_cancel_reservation(request, reservation_id):
    """Cancel a reservation."""
    reservation = get_object_or_404(
        MachineReservation, 
        id=reservation_id,
        user=request.user
    )
    
    if reservation.status != 'confirmed':
        return JsonResponse({
            'success': False, 
            'error': 'Only confirmed reservations can be cancelled'
        })
    
    reason = request.POST.get('reason', '')
    ReservationService.cancel_reservation(reservation, request.user, reason)
    
    return JsonResponse({
        'success': True,
        'message': 'Reservation cancelled successfully'
    })


@login_required
def api_my_reservations(request):
    """Get current user's reservations."""
    status_filter = request.GET.get('status', 'confirmed')
    
    reservations = MachineReservation.objects.filter(
        user=request.user
    ).select_related('machine', 'machine__location')
    
    if status_filter == 'upcoming':
        reservations = reservations.filter(
            status='confirmed',
            date__gte=timezone.now().date()
        )
    elif status_filter == 'past':
        reservations = reservations.filter(
            date__lt=timezone.now().date()
        )
    elif status_filter != 'all':
        reservations = reservations.filter(status=status_filter)
    
    reservations = reservations.order_by('-date', '-start_time')[:50]
    
    data = []
    for r in reservations:
        data.append({
            'id': r.id,
            'machine_id': r.machine_id,
            'machine_name': r.machine.name,
            'machine_type': r.machine.machine_name,
            'category': r.machine.category,
            'location': r.machine.location.name if r.machine.location else None,
            'date': str(r.date),
            'start_time': r.start_time.strftime('%H:%M'),
            'end_time': r.end_time.strftime('%H:%M'),
            'duration_minutes': r.duration_minutes,
            'purpose': r.purpose,
            'status': r.status,
            'is_active': r.is_active,
            'created_at': r.created_at.isoformat(),
        })
    
    return JsonResponse({'success': True, 'reservations': data})


# ============================================================================
# TRAINING SESSION APIs
# ============================================================================

@login_required
def api_available_trainings(request):
    """Get available training sessions for booking."""
    try:
        category = request.GET.get('category', '')
        training_id = request.GET.get('training_id')
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')

        # Parse dates - handle multiple formats
        if start_date_str:
            try:
                # Try ISO format first (YYYY-MM-DD)
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                try:
                    # Try locale format (e.g., "Sun, Nov 30, 2025")
                    start_date = datetime.strptime(start_date_str, '%a, %b %d, %Y').date()
                except ValueError:
                    # If all else fails, use today
                    start_date = timezone.now().date()
        else:
            start_date = timezone.now().date()

        if end_date_str:
            try:
                # Try ISO format first (YYYY-MM-DD)
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                try:
                    # Try locale format (e.g., "Sun, Nov 30, 2025")
                    end_date = datetime.strptime(end_date_str, '%a, %b %d, %Y').date()
                except ValueError:
                    # If all else fails, use start_date + 14 days
                    end_date = start_date + timedelta(days=14)
        else:
            end_date = start_date + timedelta(days=14)

        # Optional specific training
        training = None
        if training_id:
            from machines.models import Training
            training = Training.objects.filter(id=training_id).first()

        # Use TrainingSessionService so ids match api_book_training
        sessions = TrainingSessionService.get_available_sessions(
            category=category if category else None,
            training=training,
            start_date=start_date,
            end_date=end_date,
            user=request.user,
        )

        data = []
        for s in sessions:
            # Does the current user already have a booking for this session?
            user_booking = s.bookings.filter(user=request.user).exclude(
                status__in=['cancelled', 'no_show']
            ).first()

            data.append({
                "id": s.id,
                "training_id": s.training_id,
                "training_name": s.training.name,
                "training_level": s.training.level,
                "category": s.training.category,
                "trainer_id": s.trainer_id,
                "trainer_name": s.trainer.get_full_name() or s.trainer.email,
                "date": str(s.date),
                "start_time": s.start_time.strftime("%H:%M"),
                "end_time": s.end_time.strftime("%H:%M"),
                "duration_minutes": s.duration_minutes,
                "location": s.location.name if s.location else None,
                "max_participants": s.max_participants,
                "current_participants": s.current_participants,
                "available_spots": s.available_spots,
                "waitlist_count": s.waitlist_count,
                "status": s.status,
                "is_full": s.is_full,
                "user_booking": {
                    "id": user_booking.id,
                    "status": user_booking.status,
                    "waitlist_position": user_booking.waitlist_position,
                    "confirmation_deadline": user_booking.confirmation_deadline.isoformat() if user_booking.confirmation_deadline else None,
                } if user_booking else None,
            })

        return JsonResponse({"success": True, "sessions": data})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            "success": False,
            "error": f"Error loading sessions: {str(e)}"
        }, status=500)





@login_required
@require_POST
def api_book_training(request, session_id):
    """Book a training session."""
    session = get_object_or_404(TrainingSession, id=session_id)
    
    try:
        booking = TrainingSessionService.book_training(session, request.user)
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully {"registered" if booking.status == "registered" else "added to waitlist"}',
            'booking': {
                'id': booking.id,
                'session_id': session.id,
                'training_name': session.training.name,
                'status': booking.status,
                'waitlist_position': booking.waitlist_position,
            }
        })
        
    except ReservationValidationError as e:
        return JsonResponse({'success': False, 'error': e.message, 'code': e.code})


@login_required
@require_POST
def api_cancel_training_booking(request, booking_id):
    """Cancel a training booking."""
    booking = get_object_or_404(
        TrainingBooking,
        id=booking_id,
        user=request.user
    )
    
    if booking.status in ['completed', 'no_show']:
        return JsonResponse({
            'success': False,
            'error': 'Cannot cancel a completed or no-show booking'
        })
    
    TrainingSessionService.cancel_booking(booking)
    
    return JsonResponse({
        'success': True,
        'message': 'Booking cancelled successfully'
    })


@login_required
@require_POST
def api_confirm_waitlist_booking(request, booking_id):
    """Confirm a waitlist notification."""
    booking = get_object_or_404(
        TrainingBooking,
        id=booking_id,
        user=request.user
    )
    
    try:
        TrainingSessionService.confirm_waitlist_booking(booking)
        return JsonResponse({
            'success': True,
            'message': 'Booking confirmed successfully'
        })
    except ReservationValidationError as e:
        return JsonResponse({'success': False, 'error': e.message, 'code': e.code})


@login_required
def api_my_training_bookings(request):
    """Get current user's training bookings."""
    status_filter = request.GET.get('status', 'active')
    
    bookings = TrainingBooking.objects.filter(
        user=request.user
    ).select_related('session', 'session__training', 'session__trainer', 'session__location')
    
    if status_filter == 'active':
        bookings = bookings.filter(
            status__in=['registered', 'waitlisted', 'notified', 'confirmed'],
            session__date__gte=timezone.now().date()
        )
    elif status_filter == 'past':
        bookings = bookings.filter(
            status__in=['completed', 'no_show', 'cancelled']
        ) | bookings.filter(session__date__lt=timezone.now().date())
    elif status_filter != 'all':
        bookings = bookings.filter(status=status_filter)
    
    bookings = bookings.order_by('session__date', 'session__start_time')[:50]
    
    data = []
    for b in bookings:
        data.append({
            'id': b.id,
            'session_id': b.session_id,
            'training_name': b.session.training.name,
            'training_level': b.session.training.level,
            'category': b.session.training.category,
            'trainer_name': b.session.trainer.get_full_name() or b.session.trainer.email,
            'date': str(b.session.date),
            'start_time': b.session.start_time.strftime('%H:%M'),
            'end_time': b.session.end_time.strftime('%H:%M'),
            'location': b.session.location.name if b.session.location else None,
            'status': b.status,
            'waitlist_position': b.waitlist_position,
            'confirmation_deadline': b.confirmation_deadline.isoformat() if b.confirmation_deadline else None,
            'registered_at': b.registered_at.isoformat(),
        })
    
    return JsonResponse({'success': True, 'bookings': data})


@login_required
def api_my_training_records(request):
    """Get current user's training records (certifications)."""
    from machines.models import UserTrainingRecord
    
    records = UserTrainingRecord.objects.filter(
        user=request.user,
        status='completed'
    ).select_related('training').order_by('-completed_at')
    
    data = []
    for r in records:
        data.append({
            'id': r.id,
            'training_id': r.training_id,
            'training_name': r.training.name,
            'training_level': r.training.level,
            'category': r.training.category,
            'completed_at': r.completed_at.isoformat() if r.completed_at else None,
            'expires_at': r.expires_at.isoformat() if r.expires_at else None,
            'is_valid': r.is_valid,
        })
    
    return JsonResponse({'success': True, 'records': data})


# ============================================================================
# TEAM MEMBER APIs
# ============================================================================

@login_required
def api_my_training_sessions(request):
    """Get training sessions for the logged-in team member (as trainer)."""
    if not is_team_member(request.user):
        return JsonResponse({'success': False, 'error': 'Not a team member'}, status=403)
    
    status_filter = request.GET.get('status', 'upcoming')
    
    sessions = TrainingSession.objects.filter(
        trainer=request.user
    ).select_related('training', 'location').prefetch_related('bookings')
    
    if status_filter == 'upcoming':
        sessions = sessions.filter(
            date__gte=timezone.now().date(),
            status__in=['available', 'full']
        )
    elif status_filter == 'today':
        sessions = sessions.filter(date=timezone.now().date())
    elif status_filter == 'past':
        sessions = sessions.filter(date__lt=timezone.now().date())
    
    sessions = sessions.order_by('date', 'start_time')[:50]
    
    data = []
    for s in sessions:
        participants = []
        for b in s.bookings.filter(status__in=['registered', 'confirmed']).select_related('user'):
            participants.append({
                'id': b.id,
                'user_id': b.user_id,
                'name': b.user.get_full_name() or b.user.email,
                'email': b.user.email,
                'status': b.status,
            })
        
        data.append({
            'id': s.id,
            'training_name': s.training.name,
            'training_level': s.training.level,
            'category': s.training.category,
            'date': str(s.date),
            'start_time': s.start_time.strftime('%H:%M'),
            'end_time': s.end_time.strftime('%H:%M'),
            'location': s.location.name if s.location else None,
            'max_participants': s.max_participants,
            'current_participants': s.current_participants,
            'status': s.status,
            'participants': participants,
        })
    
    return JsonResponse({'success': True, 'sessions': data})


@login_required
@require_POST
def api_mark_training_complete(request, booking_id):
    """Mark a training booking as complete (trainer only)."""
    if not is_team_member(request.user):
        return JsonResponse({'success': False, 'error': 'Not a team member'}, status=403)
    
    booking = get_object_or_404(TrainingBooking, id=booking_id)
    
    # Verify the user is the trainer for this session
    if booking.session.trainer_id != request.user.id:
        return JsonResponse({
            'success': False, 
            'error': 'You are not the trainer for this session'
        }, status=403)
    
    if booking.status not in ['registered', 'confirmed']:
        return JsonResponse({
            'success': False,
            'error': 'Only registered or confirmed bookings can be marked complete'
        })
    
    booking.mark_complete(request.user)
    
    return JsonResponse({
        'success': True,
        'message': f'Training marked complete for {booking.user.get_full_name() or booking.user.email}'
    })


@login_required
@require_POST
def api_mark_training_no_show(request, booking_id):
    """Mark a training booking as no-show (trainer only)."""
    if not is_team_member(request.user):
        return JsonResponse({'success': False, 'error': 'Not a team member'}, status=403)
    
    booking = get_object_or_404(TrainingBooking, id=booking_id)
    
    if booking.session.trainer_id != request.user.id:
        return JsonResponse({
            'success': False, 
            'error': 'You are not the trainer for this session'
        }, status=403)
    
    booking.status = 'no_show'
    booking.save()
    
    return JsonResponse({
        'success': True,
        'message': f'Marked as no-show: {booking.user.get_full_name() or booking.user.email}'
    })


# ============================================================================
# STAFF/ADMIN APIs
# ============================================================================

@login_required
@user_passes_test(is_staff_or_admin)
def api_all_reservations(request):
    """Get all reservations (staff view)."""
    date_str = request.GET.get('date')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    location_id = request.GET.get('location_id')
    category = request.GET.get('category')
    status_filter = request.GET.get('status', 'confirmed')
    
    reservations = MachineReservation.objects.select_related(
        'machine', 'machine__location', 'user'
    )
    
    # Date filters
    if date_str:
        try:
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            reservations = reservations.filter(date=filter_date)
        except ValueError:
            pass
    elif start_date_str:
        try:
            start = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            reservations = reservations.filter(date__gte=start)
        except ValueError:
            pass
        
        if end_date_str:
            try:
                end = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                reservations = reservations.filter(date__lte=end)
            except ValueError:
                pass
    
    # Other filters
    if location_id:
        reservations = reservations.filter(machine__location_id=location_id)
    
    if category:
        reservations = reservations.filter(machine__category=category)
    
    if status_filter and status_filter != 'all':
        reservations = reservations.filter(status=status_filter)
    
    reservations = reservations.order_by('date', 'start_time')[:200]
    
    data = []
    for r in reservations:
        data.append({
            'id': r.id,
            'user_id': r.user_id,
            'user_name': r.user.get_full_name() or r.user.email,
            'user_email': r.user.email,
            'machine_id': r.machine_id,
            'machine_name': r.machine.name,
            'machine_type': r.machine.machine_name,
            'category': r.machine.category,
            'location': r.machine.location.name if r.machine.location else None,
            'date': str(r.date),
            'start_time': r.start_time.strftime('%H:%M'),
            'end_time': r.end_time.strftime('%H:%M'),
            'duration_minutes': r.duration_minutes,
            'purpose': r.purpose,
            'status': r.status,
            'created_at': r.created_at.isoformat(),
        })
    
    return JsonResponse({'success': True, 'reservations': data})


@login_required
@user_passes_test(is_staff_or_admin)
def api_all_training_sessions(request):
    """Get all training sessions (staff view)."""
    date_str = request.GET.get('date')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    category = request.GET.get('category')
    trainer_id = request.GET.get('trainer_id')
    status_filter = request.GET.get('status')
    
    sessions = TrainingSession.objects.select_related(
        'training', 'trainer', 'location'
    ).prefetch_related('bookings')
    
    # Date filters
    if date_str:
        try:
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            sessions = sessions.filter(date=filter_date)
        except ValueError:
            pass
    elif start_date_str:
        try:
            start = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            sessions = sessions.filter(date__gte=start)
        except ValueError:
            pass
        
        if end_date_str:
            try:
                end = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                sessions = sessions.filter(date__lte=end)
            except ValueError:
                pass
    
    # Other filters
    if category:
        sessions = sessions.filter(training__category=category)
    
    if trainer_id:
        sessions = sessions.filter(trainer_id=trainer_id)
    
    if status_filter and status_filter != 'all':
        sessions = sessions.filter(status=status_filter)
    
    sessions = sessions.order_by('date', 'start_time')[:200]
    
    data = []
    for s in sessions:
        registered = s.bookings.filter(status__in=['registered', 'confirmed']).count()
        waitlisted = s.bookings.filter(status='waitlisted').count()
        
        data.append({
            'id': s.id,
            'training_id': s.training_id,
            'training_name': s.training.name,
            'training_level': s.training.level,
            'category': s.training.category,
            'trainer_id': s.trainer_id,
            'trainer_name': s.trainer.get_full_name() or s.trainer.email,
            'date': str(s.date),
            'start_time': s.start_time.strftime('%H:%M'),
            'end_time': s.end_time.strftime('%H:%M'),
            'location': s.location.name if s.location else None,
            'max_participants': s.max_participants,
            'registered_count': registered,
            'waitlist_count': waitlisted,
            'status': s.status,
        })
    
    return JsonResponse({'success': True, 'sessions': data})


# ============================================================================
# MAINTENANCE APIs
# ============================================================================

@login_required
@require_POST
def api_report_maintenance(request, machine_id):
    """Report a maintenance issue for a machine."""
    from machines.models import Machine
    
    machine = get_object_or_404(Machine, id=machine_id)
    
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        issue = data.get('issue_description', '').strip()
        if not issue:
            return JsonResponse({'success': False, 'error': 'Issue description is required'})
        
        priority = data.get('priority', 'medium')
        
        maintenance = MachineMaintenance.objects.create(
            machine=machine,
            reported_by=request.user,
            issue_description=issue,
            priority=priority,
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Maintenance issue reported',
            'maintenance_id': maintenance.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff_or_admin)
def api_maintenance_queue(request):
    """Get maintenance queue (staff view)."""
    status_filter = request.GET.get('status', 'open')
    
    maintenance = MachineMaintenance.objects.select_related(
        'machine', 'machine__location', 'reported_by', 'resolved_by'
    )
    
    if status_filter == 'open':
        maintenance = maintenance.exclude(status='resolved')
    elif status_filter != 'all':
        maintenance = maintenance.filter(status=status_filter)
    
    maintenance = maintenance.order_by('-priority', '-reported_at')[:100]
    
    data = []
    for m in maintenance:
        data.append({
            'id': m.id,
            'machine_id': m.machine_id,
            'machine_name': m.machine.name,
            'machine_type': m.machine.machine_name,
            'location': m.machine.location.name if m.machine.location else None,
            'issue': m.issue_description,
            'priority': m.priority,
            'status': m.status,
            'machine_offline': m.machine_offline,
            'reported_by': m.reported_by.get_full_name() if m.reported_by else 'Unknown',
            'reported_at': m.reported_at.isoformat(),
            'resolved_at': m.resolved_at.isoformat() if m.resolved_at else None,
            'resolution_notes': m.resolution_notes,
        })
    
    return JsonResponse({'success': True, 'maintenance': data})


@login_required
@user_passes_test(is_staff_or_admin)
@require_POST
def api_take_machine_offline(request, maintenance_id):
    """Take a machine offline for maintenance."""
    maintenance = get_object_or_404(MachineMaintenance, id=maintenance_id)
    maintenance.take_offline(request.user)
    
    # Cancel affected reservations
    from .models import MachineReservation
    affected = MachineReservation.objects.filter(
        machine=maintenance.machine,
        date__gte=timezone.now().date(),
        status='confirmed'
    )
    
    cancelled_count = 0
    for r in affected:
        r.cancel(f'Machine taken offline for maintenance: {maintenance.issue_description[:100]}')
        cancelled_count += 1
    
    return JsonResponse({
        'success': True,
        'message': f'Machine taken offline. {cancelled_count} reservation(s) cancelled.',
    })


@login_required
@user_passes_test(is_staff_or_admin)
@require_POST
def api_resolve_maintenance(request, maintenance_id):
    """Resolve a maintenance issue."""
    maintenance = get_object_or_404(MachineMaintenance, id=maintenance_id)
    
    notes = request.POST.get('resolution_notes', '')
    maintenance.resolve(request.user, notes)
    
    return JsonResponse({
        'success': True,
        'message': 'Maintenance issue resolved. Machine is back online.',
    })


# ============================================================================
# BLACKOUT PERIOD APIs
# ============================================================================

@login_required
@user_passes_test(is_staff_or_admin)
def api_blackout_periods(request):
    """Get all blackout periods."""
    blackouts = BlackoutPeriod.objects.select_related(
        'location', 'machine', 'created_by'
    ).order_by('-start_datetime')[:100]
    
    data = []
    for b in blackouts:
        data.append({
            'id': b.id,
            'scope': b.scope,
            'location': b.location.name if b.location else None,
            'category': b.category,
            'machine': b.machine.name if b.machine else None,
            'start_datetime': b.start_datetime.isoformat(),
            'end_datetime': b.end_datetime.isoformat(),
            'reason': b.reason,
            'blocks_reservations': b.blocks_reservations,
            'blocks_trainings': b.blocks_trainings,
            'created_by': b.created_by.get_full_name() if b.created_by else None,
            'created_at': b.created_at.isoformat(),
        })
    
    return JsonResponse({'success': True, 'blackouts': data})


@login_required
@user_passes_test(is_staff_or_admin)
@require_POST
def api_create_blackout(request):
    """Create a new blackout period."""
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        scope = data.get('scope', 'global')
        start_str = data.get('start_datetime')
        end_str = data.get('end_datetime')
        reason = data.get('reason', '').strip()
        
        if not all([start_str, end_str, reason]):
            return JsonResponse({
                'success': False, 
                'error': 'Start time, end time, and reason are required'
            })
        
        start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
        
        blackout = BlackoutPeriod(
            scope=scope,
            start_datetime=start_dt,
            end_datetime=end_dt,
            reason=reason,
            internal_notes=data.get('internal_notes', ''),
            blocks_reservations=data.get('blocks_reservations', True),
            blocks_trainings=data.get('blocks_trainings', True),
            created_by=request.user,
        )
        
        # Set scope-specific fields
        if scope == 'location':
            blackout.location_id = data.get('location_id')
        elif scope == 'category':
            blackout.category = data.get('category')
        elif scope == 'machine':
            blackout.machine_id = data.get('machine_id')
        
        blackout.full_clean()
        blackout.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Blackout period created',
            'blackout_id': blackout.id
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff_or_admin)
@require_POST
def api_delete_blackout(request, blackout_id):
    """Delete a blackout period."""
    blackout = get_object_or_404(BlackoutPeriod, id=blackout_id)
    blackout.delete()
    
    return JsonResponse({
        'success': True,
        'message': 'Blackout period deleted'
    })


# ============================================================================
# PAGE VIEWS (Templates)
# ============================================================================

@login_required
def my_reservations(request):
    """Student's machine reservations page"""
    return render(request, 'reservations/my_reservations.html')


@login_required
def training_browser(request):
    """Browse and book training sessions"""
    return render(request, 'reservations/training_browser.html')


@login_required
def my_training_progress(request):
    """Student's training progress and history"""
    return render(request, 'reservations/my_training_progress.html')


@login_required
@user_passes_test(is_staff_or_admin)
def staff_reservations_hub(request):
    """Staff hub page for reservations management"""
    return render(request, 'reservations/staff_reservations_hub.html')


@login_required
@user_passes_test(is_staff_or_admin)
def staff_reservations_dashboard(request):
    """Staff dashboard for viewing all reservations"""
    return render(request, 'reservations/staff_reservations_dashboard.html')


@login_required
@user_passes_test(is_staff_or_admin)
def staff_training_dashboard(request):
    """Staff dashboard for viewing all training sessions"""
    return render(request, 'reservations/staff_training_dashboard.html')


@login_required
@user_passes_test(is_staff_or_admin)
def maintenance_management(request):
    """Staff page for managing machine maintenance"""
    return render(request, 'reservations/maintenance_management.html')


@login_required
@user_passes_test(is_staff_or_admin)
def blackout_management(request):
    """Staff page for managing blackout periods"""
    return render(request, 'reservations/blackout_management.html')


@login_required
def team_my_training_sessions(request):
    """Team member's training sessions they're conducting"""
    # Check if user is a team member
    if not is_team_member(request.user) and not is_staff_or_admin(request.user):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You must be a team member to access this page")
    
    return render(request, 'reservations/team_my_training_sessions.html')
