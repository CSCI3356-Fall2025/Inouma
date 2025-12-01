from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils.dateparse import parse_date
from datetime import datetime, timedelta
import json

from .models import (
    Semester, DailyOperatingHours, ShiftRequirement, LocationGroup,
    TeamMemberProfile, Unavailability, Shift, SchedulePublication,
    ShiftChangeRequest
)
from locations.models import Location
from .weekly_scheduler import WeeklyScheduler


def is_staff_user(user):
    """Check if user is staff"""
    return user.is_staff or user.is_superuser


# ==========================================
# STAFF VIEWS
# ==========================================

@login_required
@user_passes_test(is_staff_user)
def schedule_management(request):
    """Main schedule management page"""
    active_semester = Semester.objects.filter(is_active=True).first()
    
    context = {
        'active_semester': active_semester,
    }
    
    return render(request, 'scheduling/schedule_management.html', context)


@login_required
@user_passes_test(is_staff_user)
def schedule_landing(request):
    """Schedule management landing page with options"""
    active_semester = Semester.objects.filter(is_active=True).first()
    total_team_members = TeamMemberProfile.objects.count()
    
    # Get total shifts for this week if there's an active semester
    total_shifts = 0
    if active_semester:
        from datetime import date, timedelta
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=7)
        
        total_shifts = Shift.objects.filter(
            semester=active_semester,
            date__gte=week_start,
            date__lt=week_end
        ).count()
    
    context = {
        'active_semester': active_semester,
        'total_team_members': total_team_members,
        'total_shifts': total_shifts,
    }
    
    return render(request, 'scheduling/schedule_landing.html', context)


@login_required
@user_passes_test(is_staff_user)
def view_schedule(request):
    """View current schedule"""
    semesters = Semester.objects.all().order_by('-start_date')
    
    context = {
        'semesters': semesters
    }
    
    return render(request, 'scheduling/view_schedule.html', context)


@login_required
@user_passes_test(is_staff_user)
def configure_semester(request):
    """Configure semester settings"""
    semesters = Semester.objects.all().order_by('-start_date')
    locations = Location.objects.all().order_by('name')
    location_groups = LocationGroup.objects.all().order_by('name')
    
    context = {
        'semesters': semesters,
        'locations': locations,
        'location_groups': location_groups,
    }
    
    return render(request, 'scheduling/configure_semester.html', context)


@login_required
@user_passes_test(is_staff_user)
def api_get_semester_config(request, semester_id):
    """Get semester configuration for editing"""
    semester = get_object_or_404(Semester, id=semester_id)
    
    # Get operating hours
    operating_hours = {}
    for oh in DailyOperatingHours.objects.filter(semester=semester):
        operating_hours[oh.day_of_week] = {
            'id': oh.id,
            'is_closed': oh.is_closed,
            'training_disabled': oh.training_disabled,
            'open_hours_start': oh.open_hours_start.strftime('%H:%M') if oh.open_hours_start else None,
            'open_hours_end': oh.open_hours_end.strftime('%H:%M') if oh.open_hours_end else None,
            'training_start': oh.training_start.strftime('%H:%M') if oh.training_start else None,
            'training_end': oh.training_end.strftime('%H:%M') if oh.training_end else None,
        }
    
    # Get shift requirements
    shift_requirements = []
    for req in ShiftRequirement.objects.filter(semester=semester).select_related('location', 'location_group'):
        shift_requirements.append({
            'id': req.id,
            'day_of_week': req.day_of_week,
            'time_start': req.time_start.strftime('%H:%M'),
            'time_end': req.time_end.strftime('%H:%M'),
            'location_id': req.location_id,
            'location_name': req.location.name if req.location else None,
            'location_group_id': req.location_group_id,
            'location_group_name': req.location_group.name if req.location_group else None,
            'hosts_required': req.hosts_required,
            'floaters_required': req.floaters_required,
        })
    
    # Get holidays
    holidays = semester.holidays if semester.holidays else []
    
    return JsonResponse({
        'semester': {
            'id': semester.id,
            'name': semester.name,
            'start_date': semester.start_date.isoformat(),
            'end_date': semester.end_date.isoformat(),
        },
        'operating_hours': operating_hours,
        'shift_requirements': shift_requirements,
        'holidays': holidays,
    })


@login_required
@user_passes_test(is_staff_user)
@require_POST
def api_save_semester_config(request):
    """Save semester configuration"""
    try:
        data = json.loads(request.body)
        semester_id = data.get('semester_id')
        
        semester = get_object_or_404(Semester, id=semester_id)
        
        # Save operating hours
        operating_hours_data = data.get('operating_hours', {})
        for day_str, day_data in operating_hours_data.items():
            day_of_week = int(day_str)
            
            oh, created = DailyOperatingHours.objects.update_or_create(
                semester=semester,
                day_of_week=day_of_week,
                defaults={
                    'is_closed': day_data.get('is_closed', False),
                    'training_disabled': day_data.get('training_disabled', False),
                    'open_hours_start': day_data.get('open_hours_start') or None,
                    'open_hours_end': day_data.get('open_hours_end') or None,
                    'training_start': day_data.get('training_start') or None,
                    'training_end': day_data.get('training_end') or None,
                }
            )
        
        # Save shift requirements
        shift_requirements_data = data.get('shift_requirements', [])
        
        # Get existing requirement IDs
        existing_ids = set(ShiftRequirement.objects.filter(semester=semester).values_list('id', flat=True))
        updated_ids = set()
        
        for req_data in shift_requirements_data:
            req_id = req_data.get('id')
            is_new = req_data.get('isNew', False) or not isinstance(req_id, int) or req_id > 1000000000
            
            location = None
            location_group = None
            if req_data.get('location_id'):
                location = Location.objects.filter(id=req_data['location_id']).first()
            if req_data.get('location_group_id'):
                location_group = LocationGroup.objects.filter(id=req_data['location_group_id']).first()
            
            if is_new:
                # Create new requirement
                ShiftRequirement.objects.create(
                    semester=semester,
                    day_of_week=req_data['day_of_week'],
                    time_start=req_data['time_start'],
                    time_end=req_data['time_end'],
                    location=location,
                    location_group=location_group,
                    hosts_required=req_data.get('hosts_required', 0),
                    floaters_required=req_data.get('floaters_required', 0),
                )
            else:
                # Update existing
                ShiftRequirement.objects.filter(id=req_id).update(
                    day_of_week=req_data['day_of_week'],
                    time_start=req_data['time_start'],
                    time_end=req_data['time_end'],
                    location=location,
                    location_group=location_group,
                    hosts_required=req_data.get('hosts_required', 0),
                    floaters_required=req_data.get('floaters_required', 0),
                )
                updated_ids.add(req_id)
        
        # Delete removed requirements
        ids_to_delete = existing_ids - updated_ids
        ShiftRequirement.objects.filter(id__in=ids_to_delete).delete()
        
        # Save holidays
        holidays = data.get('holidays', [])
        semester.holidays = holidays
        semester.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@user_passes_test(is_staff_user)
def manage_availability(request):
    """Manage team member availability and hours"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    semesters = Semester.objects.all().order_by('-start_date')
    users = User.objects.filter(is_active=True).order_by('first_name', 'last_name', 'email')
    
    context = {
        'semesters': semesters,
        'users': users,
    }
    
    return render(request, 'scheduling/manage_availability.html', context)


@login_required
@user_passes_test(is_staff_user)
def api_get_location_groups(request):
    """Get all location groups"""
    groups = LocationGroup.objects.all().prefetch_related('locations')
    
    data = []
    for group in groups:
        data.append({
            'id': group.id,
            'name': group.name,
            'description': group.description,
            'locations': [{'id': loc.id, 'name': loc.name} for loc in group.locations.all()],
        })
    
    return JsonResponse({'groups': data})


@login_required
@user_passes_test(is_staff_user)
@require_POST
def api_save_location_group(request):
    """Create or update a location group"""
    try:
        data = json.loads(request.body)
        group_id = data.get('id')
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        location_ids = data.get('location_ids', [])
        
        if not name:
            return JsonResponse({'success': False, 'error': 'Name is required'}, status=400)
        
        if not location_ids:
            return JsonResponse({'success': False, 'error': 'At least one location is required'}, status=400)
        
        if group_id:
            # Update existing
            group = get_object_or_404(LocationGroup, id=group_id)
            group.name = name
            group.description = description
            group.save()
        else:
            # Create new
            group = LocationGroup.objects.create(name=name, description=description)
        
        # Update locations
        group.locations.set(location_ids)
        
        return JsonResponse({
            'success': True,
            'group': {
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'locations': [{'id': loc.id, 'name': loc.name} for loc in group.locations.all()],
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@user_passes_test(is_staff_user)
@require_POST
def api_delete_location_group(request, group_id):
    """Delete a location group"""
    try:
        group = get_object_or_404(LocationGroup, id=group_id)
        group.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@user_passes_test(is_staff_user)
def review_requests(request):
    """Review shift swap/cancellation requests"""
    # Placeholder
    return render(request, 'scheduling/review_requests.html', {})


@login_required
@user_passes_test(is_staff_user)
def auto_schedule_page(request):
    """Auto-schedule page"""
    semesters = Semester.objects.filter(is_archived=False).order_by('-start_date')
    
    context = {
        'semesters': semesters
    }
    
    return render(request, 'scheduling/auto_schedule.html', context)


@login_required
@user_passes_test(is_staff_user)
def manage_semesters(request):
    """Manage semesters"""
    # Placeholder
    return render(request, 'scheduling/manage_semesters.html', {})


@login_required
@user_passes_test(is_staff_user)
def publish_schedule_page(request):
    """Publish schedule page"""
    from django.conf import settings
    
    # Get default from email from settings
    default_from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'hatchery@bc.edu')
    
    return render(request, 'scheduling/publish_schedule.html', {
        'default_from_email': default_from_email
    })


from .weekly_scheduler import WeeklyScheduler


@login_required
@user_passes_test(is_staff_user)
@require_POST
def run_auto_scheduler(request):
    """Run the auto-scheduler algorithm"""
    
    try:
        data = json.loads(request.body)
        semester_id = data.get('semester_id')
        
        if not semester_id:
            return JsonResponse({
                'success': False,
                'message': 'Semester ID required'
            }, status=400)
        
        semester = get_object_or_404(Semester, id=semester_id)
        
        # Run the weekly scheduler
        scheduler = WeeklyScheduler(semester)
        result = scheduler.run()
        
        # Format conflicts for response
        conflicts_formatted = [
            {
                'type': c.get('type'),
                'day': c.get('day'),
                'time': c.get('time'),
                'location': str(c.get('location', ''))
            }
            for c in result.get('conflicts', [])
        ]
        
        return JsonResponse({
            'success': result['success'],
            'shifts_created': result['shifts_created'],
            'conflicts': conflicts_formatted,
            'message': result['message']
        })
        
    except Exception as e:
        import traceback
        print(f"Error in auto-scheduler: {e}")
        print(traceback.format_exc())
        
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        }, status=500)


@login_required
def clear_schedule(request, semester_id):
    """Clear all shifts for a semester"""
    # Check staff permission manually for better AJAX error handling
    if not (request.user.is_staff or request.user.is_superuser):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({'success': False, 'error': 'Permission denied - staff access required'}, status=403)
        return redirect('scheduling:schedule_landing')
    
    semester = get_object_or_404(Semester, id=semester_id)
    
    if request.method == 'POST':
        count = Shift.objects.filter(semester=semester).delete()[0]
        
        # Check if it's an AJAX/fetch request (multiple ways to detect)
        is_ajax = (
            request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
            request.content_type == 'application/json' or
            'application/json' in request.headers.get('Accept', '') or
            request.headers.get('X-CSRFToken')  # fetch requests typically include this
        )
        
        if is_ajax:
            return JsonResponse({
                'success': True,
                'deleted_count': count,
                'message': f'Cleared {count} shifts from {semester.name}'
            })
        
        messages.success(request, f'Cleared {count} shifts from {semester.name}')
        return redirect('scheduling:schedule_landing')
    
    # For GET requests, check if it's expecting JSON
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    return render(request, 'scheduling/confirm_clear.html', {
        'semester': semester
    })


# ==========================================
# API ENDPOINTS
# ==========================================

@login_required
def api_get_semesters(request):
    """Get list of all semesters"""
    semesters = Semester.objects.all().order_by('-start_date')
    
    data = [{
        'id': s.id,
        'name': s.name,
        'type': s.semester_type,
        'year': s.year,
        'start_date': s.start_date.isoformat(),
        'end_date': s.end_date.isoformat(),
        'is_active': s.is_active
    } for s in semesters]
    
    return JsonResponse({'semesters': data})


@login_required
def api_get_weeks(request):
    """Get list of weeks for a semester"""
    semester_id = request.GET.get('semester_id')
    
    if not semester_id:
        return JsonResponse({'weeks': []})
    
    semester = get_object_or_404(Semester, id=semester_id)
    
    # Generate weeks (Monday to Sunday)
    weeks = []
    current = semester.start_date
    
    # Find the Monday of the week containing start_date
    days_since_monday = current.weekday()
    if days_since_monday != 0:
        current = current - timedelta(days=days_since_monday)
    
    week_num = 1
    while current <= semester.end_date:
        week_end = current + timedelta(days=6)
        if week_end > semester.end_date:
            week_end = semester.end_date
        
        weeks.append({
            'value': current.isoformat(),
            'label': f"Week {week_num}: {current.strftime('%b %d')} – {week_end.strftime('%b %d')}",
            'start': current.isoformat(),
            'end': week_end.isoformat()
        })
        
        current += timedelta(days=7)
        week_num += 1
    
    return JsonResponse({'weeks': weeks})


@login_required
def api_get_shifts(request):
    """Get shifts for display"""
    semester_id = request.GET.get('semester_id')
    week_start = request.GET.get('week_start')
    
    filters = {}
    
    if semester_id:
        filters['semester_id'] = semester_id
    
    if week_start:
        week_date = parse_date(week_start)
        week_end = week_date + timedelta(days=7)
        filters['date__gte'] = week_date
        filters['date__lt'] = week_end
    
    # Get shifts grouped by day of week for model week
    if semester_id and not week_start:
        # Get one week's worth of shifts to show the model
        semester = Semester.objects.get(id=semester_id)
        
        # Find first week with shifts
        first_shift = Shift.objects.filter(semester_id=semester_id).order_by('date').first()
        
        if first_shift:
            # Get that week's shifts
            week_start_date = first_shift.date - timedelta(days=first_shift.date.weekday())
            week_end_date = week_start_date + timedelta(days=7)
            
            filters['date__gte'] = week_start_date
            filters['date__lt'] = week_end_date
    
    shifts = Shift.objects.filter(**filters).select_related(
        'user', 'location', 'location_group'
    ).order_by('date', 'start_time')
    
    data = []
    for shift in shifts:
        # Get location info
        location_info = None
        if shift.shift_type == 'open_hours':
            if shift.location:
                location_info = shift.location.name
            elif shift.location_group:
                location_info = shift.location_group.name
        
        data.append({
            'id': shift.id,
            'date': shift.date.isoformat(),
            'start': shift.start_time.strftime('%H:%M'),
            'end': shift.end_time.strftime('%H:%M'),
            'user': shift.user.get_full_name() or shift.user.email,
            'user_id': shift.user.id,
            'shift_type': shift.shift_type,
            'shift_type_display': shift.get_shift_type_display(),
            'team': shift.team_category,
            'location': location_info,
            'status': shift.status,
            'duration_hours': shift.duration_hours()
        })
    
    return JsonResponse({'shifts': data})


@login_required
def api_get_team_members(request):
    """Get list of team members (users with Team Member or Staff role)"""
    from django.contrib.auth import get_user_model
    from accounts.models import TrainerAvailability, TrainerProfile, StudentProfile
    
    User = get_user_model()
    semester_id = request.GET.get('semester_id')
    
    # Get users who are Team Members or Staff
    team_users = User.objects.filter(
        role__in=['Team Member', 'Staff'],
        is_active=True
    ).order_by('first_name', 'last_name')
    
    data = []
    for user in team_users:
        # Get trainer profile if exists
        trainer_profile = getattr(user, 'trainer_profile', None)
        
        # Get student profile for birthday/grad year
        student_profile = None
        try:
            student_profile = user.student_profile
        except:
            pass
        
        # Get unavailability from Unavailability model (scheduling)
        unavailability = {}
        semester_id = request.GET.get('semester_id')
        if semester_id:
            unavail_records = Unavailability.objects.filter(user=user, semester_id=semester_id)
            
            for i in range(7):
                day_slots = unavail_records.filter(day_of_week=i)
                slots = []
                for slot in day_slots:
                    slots.append({
                        'start': slot.start_time.strftime('%H:%M') if slot.start_time else '09:00',
                        'end': slot.end_time.strftime('%H:%M') if slot.end_time else '17:00',
                        'reason': slot.reason or ''
                    })
                unavailability[i] = slots
        
        # Get profile picture URL
        profile_pic = None
        if user.profile_picture:
            profile_pic = user.profile_picture.url
        
        # Try to get team member profile for hours
        team_profile = None
        try:
            team_profile = TeamMemberProfile.objects.get(user=user)
        except TeamMemberProfile.DoesNotExist:
            pass
        
        # Get team assignment - prefer User.team_assignment, fallback to team_profile.team
        team = user.team_assignment or ''
        if not team and team_profile:
            team = team_profile.team or ''
        
        data.append({
            'user_id': str(user.id),
            'name': user.get_full_name() or user.email.split('@')[0],
            'email': user.email,
            'profile_picture': profile_pic,
            'is_trainer': user.is_trainer,
            'is_team_lead': user.is_team_lead,
            'team': team,
            'min_weekly_hours': team_profile.min_weekly_hours if team_profile else 0,
            'max_weekly_hours': team_profile.max_weekly_hours if team_profile else 15,
            'shift_preference': team_profile.shift_preference if team_profile else 'no_preference',
            'scheduled_hours': 0,  # TODO: Calculate from actual shifts
            'unavailability': unavailability,
            'birthday': student_profile.birthday.isoformat() if student_profile and student_profile.birthday else None,
            'grad_year': student_profile.graduation_year if student_profile else None,
            'phone': team_profile.phone if team_profile else '',
            'notes': team_profile.notes if team_profile else '',
            'trainer_specialty': trainer_profile.specialty if trainer_profile else '',
            'trainer_bio': trainer_profile.bio if trainer_profile else '',
            'trainer_certifications': trainer_profile.certifications if trainer_profile else '',
        })
    
    return JsonResponse({'members': data})


@login_required
@user_passes_test(is_staff_user)
@require_POST
def api_save_team_member(request):
    """Save team member settings and unavailability"""
    try:
        from django.contrib.auth import get_user_model
        from accounts.models import TrainerProfile
        
        data = json.loads(request.body)
        user_id = data.get('user_id')
        
        if not user_id:
            return JsonResponse({'success': False, 'error': 'User is required'}, status=400)
        
        User = get_user_model()
        user = get_object_or_404(User, id=user_id)
        
        # Get team assignment
        team = data.get('team', '')
        
        # Update user fields
        user.is_team_lead = data.get('is_team_lead', False)
        user.is_trainer = data.get('is_trainer', user.is_trainer)
        user.team_assignment = team  # Save team to User model
        user.save()
        
        # Get or create TeamMemberProfile for scheduling data
        team_profile, _ = TeamMemberProfile.objects.get_or_create(user=user)
        team_profile.min_weekly_hours = data.get('min_weekly_hours', 0)
        team_profile.max_weekly_hours = data.get('max_weekly_hours', 15)
        team_profile.expected_weekly_hours = data.get('max_weekly_hours', 15)
        team_profile.shift_preference = data.get('shift_preference', 'no_preference')
        team_profile.team = team  # Also save to TeamMemberProfile
        team_profile.is_trainer = data.get('is_trainer', team_profile.is_trainer)
        team_profile.is_team_lead = data.get('is_team_lead', False)
        team_profile.save()
        
        # Update TrainerProfile if trainer data provided
        if data.get('trainer_specialty') or data.get('trainer_bio') or data.get('trainer_certifications'):
            trainer_profile, _ = TrainerProfile.objects.get_or_create(user=user)
            if data.get('trainer_specialty'):
                trainer_profile.specialty = data['trainer_specialty']
            if data.get('trainer_bio'):
                trainer_profile.bio = data['trainer_bio']
            if data.get('trainer_certifications'):
                trainer_profile.certifications = data['trainer_certifications']
            trainer_profile.save()
        
        # Update unavailability - clear existing and create new for current semester
        semester_id = data.get('semester_id')
        if semester_id:
            Unavailability.objects.filter(user=user, semester_id=semester_id).delete()
            
            unavailability_data = data.get('unavailability', {})
            for day_str, slots in unavailability_data.items():
                day_of_week = int(day_str)
                
                for slot in slots:
                    if slot.get('start') and slot.get('end'):
                        Unavailability.objects.create(
                            user=user,
                            semester_id=semester_id,
                            day_of_week=day_of_week,
                            start_time=slot['start'],
                            end_time=slot['end'],
                            reason=slot.get('reason', '')
                        )
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@user_passes_test(is_staff_user)
def api_shift_stats(request):
    """Get statistics about shifts"""
    semester_id = request.GET.get('semester_id')
    
    if not semester_id:
        return JsonResponse({'stats': {}})
    
    shifts = Shift.objects.filter(semester_id=semester_id)
    
    stats = {
        'total_shifts': shifts.count(),
        'open_hours': shifts.filter(shift_type='open_hours').count(),
        'training': shifts.filter(shift_type='training').count(),
        'floater': shifts.filter(shift_type='floater').count(),
        'team_members_scheduled': shifts.values('user').distinct().count(),
    }
    
    # Calculate total hours
    total_hours = sum(shift.duration_hours() for shift in shifts)
    stats['total_hours'] = round(total_hours, 1)
    
    return JsonResponse({'stats': stats})


@login_required
def api_get_categories(request):
    """Get machine categories for team assignments"""
    # Use CATEGORY_CHOICES from machines app
    categories = [
        {'id': 1, 'name': 'Laser'},
        {'id': 2, 'name': 'Vinyl'},
        {'id': 3, 'name': 'Woodworking'},
        {'id': 4, 'name': 'Textile'},
        {'id': 5, 'name': 'Metalworking'},
        {'id': 6, 'name': '3D Printing'},
        {'id': 7, 'name': 'Electronics'},
    ]
    
    return JsonResponse({'categories': categories})


# ==========================================
# TEAM MEMBER VIEWS
# ==========================================

@login_required
def my_availability(request):
    """Team member enters their availability"""
    active_semester = Semester.objects.filter(is_active=True).first()
    
    if not active_semester:
        messages.error(request, 'No active semester found')
        return redirect('home')
    
    # Get or create profile
    profile, created = TeamMemberProfile.objects.get_or_create(
        user=request.user
    )
    
    # Get existing unavailabilities
    unavailabilities = Unavailability.objects.filter(
        user=request.user,
        semester=active_semester
    ).order_by('day_of_week', 'start_time')
    
    context = {
        'semester': active_semester,
        'profile': profile,
        'unavailabilities': unavailabilities
    }
    
    return render(request, 'scheduling/my_availability.html', context)


@login_required
def my_schedule(request):
    """Team member views their schedule"""
    active_semester = Semester.objects.filter(is_active=True).first()
    
    if not active_semester:
        messages.error(request, 'No active semester found')
        return redirect('home')
    
    # Get user's shifts
    shifts = Shift.objects.filter(
        user=request.user,
        semester=active_semester
    ).order_by('date', 'start_time')
    
    context = {
        'semester': active_semester,
        'shifts': shifts
    }
    
    return render(request, 'scheduling/my_schedule.html', context)


# ==========================================
# MANAGE SEMESTERS
# ==========================================

@login_required
@user_passes_test(is_staff_user)
def manage_semesters(request):
    """Manage semesters page"""
    return render(request, 'scheduling/manage_semesters.html')


@login_required
@user_passes_test(is_staff_user)
def api_get_semesters(request):
    """Get all semesters with stats"""
    semesters = Semester.objects.all().order_by('-start_date')
    
    data = []
    for sem in semesters:
        # Get holiday count
        holidays_count = len(sem.holidays) if sem.holidays else 0
        
        # Get team members count
        team_members_count = TeamMemberProfile.objects.filter(
            semester=sem
        ).count()
        
        # If no semester-specific members, count all active
        if team_members_count == 0:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            team_members_count = User.objects.filter(
                role__in=['Team Member', 'Staff'],
                is_active=True
            ).count()
        
        # Get shifts count and total hours
        shifts = Shift.objects.filter(semester=sem)
        shifts_count = shifts.count()
        total_hours = 0
        for shift in shifts:
            if hasattr(shift, 'duration_hours'):
                total_hours += shift.duration_hours()
        
        data.append({
            'id': sem.id,
            'name': sem.name,
            'semester_type': sem.semester_type,
            'year': sem.year,
            'start_date': sem.start_date.isoformat(),
            'end_date': sem.end_date.isoformat(),
            'is_active': sem.is_active,
            'is_archived': getattr(sem, 'is_archived', False),
            'holidays_count': holidays_count,
            'team_members_count': team_members_count,
            'shifts_count': shifts_count,
            'total_hours': round(total_hours, 1)
        })
    
    return JsonResponse({'semesters': data})


@login_required
@user_passes_test(is_staff_user)
@require_POST
def api_save_semester(request):
    """Create or update a semester"""
    try:
        data = json.loads(request.body)
        
        semester_id = data.get('id')
        name = data.get('name', '').strip()
        semester_type = data.get('semester_type')
        year = data.get('year')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        is_active = data.get('is_active', False)
        
        if not name:
            return JsonResponse({'success': False, 'error': 'Name is required'}, status=400)
        
        if semester_id:
            semester = get_object_or_404(Semester, id=semester_id)
            semester.name = name
            semester.semester_type = semester_type
            semester.year = year
            semester.start_date = start_date
            semester.end_date = end_date
            semester.is_active = is_active
            semester.save()
        else:
            semester = Semester.objects.create(
                name=name,
                semester_type=semester_type,
                year=year,
                start_date=start_date,
                end_date=end_date,
                is_active=is_active
            )
            
            # Create default operating hours for the new semester
            for day in range(7):
                is_weekend = day >= 5
                DailyOperatingHours.objects.create(
                    semester=semester,
                    day_of_week=day,
                    is_closed=is_weekend,
                    open_hours_start='09:00' if not is_weekend else None,
                    open_hours_end='17:00' if not is_weekend else None,
                    training_start='09:00' if not is_weekend else None,
                    training_end='17:00' if not is_weekend else None
                )
        
        return JsonResponse({'success': True, 'id': semester.id})
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@user_passes_test(is_staff_user)
@require_POST
def api_set_active_semester(request):
    """Set a semester as active"""
    try:
        data = json.loads(request.body)
        semester_id = data.get('id')
        
        semester = get_object_or_404(Semester, id=semester_id)
        
        # Deactivate all other semesters
        Semester.objects.filter(is_active=True).update(is_active=False)
        
        # Activate this one
        semester.is_active = True
        semester.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@user_passes_test(is_staff_user)
@require_POST
def api_archive_semester(request):
    """Archive a semester"""
    try:
        data = json.loads(request.body)
        semester_id = data.get('id')
        
        semester = get_object_or_404(Semester, id=semester_id)
        
        # Add is_archived field if not exists
        if not hasattr(semester, 'is_archived'):
            # Use a workaround - store in holidays or create new field
            pass
        
        semester.is_archived = True
        semester.is_active = False
        semester.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@user_passes_test(is_staff_user)
@require_POST
def api_unarchive_semester(request):
    """Unarchive a semester"""
    try:
        data = json.loads(request.body)
        semester_id = data.get('id')
        
        semester = get_object_or_404(Semester, id=semester_id)
        semester.is_archived = False
        semester.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@user_passes_test(is_staff_user)
@require_POST
def api_delete_semester(request):
    """Permanently delete a semester"""
    try:
        data = json.loads(request.body)
        semester_id = data.get('id')
        
        semester = get_object_or_404(Semester, id=semester_id)
        
        # Don't allow deleting active semester
        if semester.is_active:
            return JsonResponse({'success': False, 'error': 'Cannot delete active semester'}, status=400)
        
        semester.delete()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ==========================================
# PUBLISH SCHEDULE
# ==========================================

@login_required
@user_passes_test(is_staff_user)
def api_get_publish_history(request):
    """Get publication history for a semester"""
    semester_id = request.GET.get('semester_id')
    
    if not semester_id:
        return JsonResponse({'history': []})
    
    publications = SchedulePublication.objects.filter(
        semester_id=semester_id
    ).order_by('-published_at')[:20]
    
    history = []
    for pub in publications:
        history.append({
            'id': pub.id,
            'published_at': pub.published_at.isoformat(),
            'weeks_count': pub.weeks_count,
            'recipients_count': pub.recipients_count,
            'calendar_invites': pub.calendar_invites_sent,
            'email_sent': pub.email_sent,
            'status': pub.status
        })
    
    return JsonResponse({'history': history})


@login_required
@user_passes_test(is_staff_user)
@require_POST
def api_publish_schedule(request):
    """Publish schedule - send calendar invites and emails"""
    try:
        data = json.loads(request.body)
        
        semester_id = data.get('semester_id')
        weeks = data.get('weeks', [])
        recipients = data.get('recipients', [])
        send_calendar = data.get('send_calendar_invites', False)
        send_email = data.get('send_email', False)
        from_email = data.get('from_email', 'hatchery@bc.edu')
        email_subject = data.get('email_subject', 'Your Hatchery Schedule')
        email_message = data.get('email_message', '')
        
        semester = get_object_or_404(Semester, id=semester_id)
        
        # Get shifts for selected weeks and recipients
        shifts = Shift.objects.filter(
            semester=semester,
            user_id__in=recipients
        ).select_related('user')
        
        # Filter by weeks if specified
        if weeks:
            from datetime import datetime as dt
            week_dates = [dt.fromisoformat(w).date() for w in weeks]
            # Filter shifts that fall within selected weeks
            filtered_shifts = []
            for shift in shifts:
                shift_week_start = shift.date - timedelta(days=shift.date.weekday())
                if shift_week_start in week_dates:
                    filtered_shifts.append(shift)
            shifts = filtered_shifts
        
        calendar_invites_sent = 0
        emails_sent = 0
        email_errors = []
        
        # Group shifts by user for email
        shifts_by_user = {}
        for shift in shifts:
            if shift.user_id not in shifts_by_user:
                shifts_by_user[shift.user_id] = {
                    'user': shift.user,
                    'shifts': []
                }
            shifts_by_user[shift.user_id]['shifts'].append(shift)
        
        if send_calendar:
            # TODO: Implement Google Calendar API integration
            # For now, we'll just count them and update status
            calendar_invites_sent = len(shifts)
            
            # Update shift status to published
            for shift in shifts:
                if hasattr(shift, 'save'):
                    shift.status = 'published'
                    shift.save()
        
        if send_email:
            from django.core.mail import send_mail
            from django.template.loader import render_to_string
            from django.conf import settings
            
            for user_id, user_data in shifts_by_user.items():
                user = user_data['user']
                user_shifts = user_data['shifts']
                
                # Sort shifts by date
                user_shifts.sort(key=lambda s: (s.date, s.start_time))
                
                # Build email body
                shift_lines = []
                for shift in user_shifts:
                    day_name = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][shift.date.weekday()]
                    date_str = shift.date.strftime('%b %d')
                    time_str = f"{shift.start_time.strftime('%I:%M %p')} - {shift.end_time.strftime('%I:%M %p')}"
                    shift_type = shift.shift_type.replace('_', ' ').title()
                    location = getattr(shift, 'location', None)
                    location_str = f" @ {location.name}" if location else ""
                    
                    shift_lines.append(f"  • {day_name} {date_str}: {time_str} - {shift_type}{location_str}")
                
                # Compose email
                email_body = f"""Hi {user.first_name or user.email.split('@')[0]},

Your schedule for {semester.name} has been published. Here are your assigned shifts:

{chr(10).join(shift_lines)}

Total shifts: {len(user_shifts)}
"""
                if email_message:
                    email_body += f"\n---\n{email_message}\n"
                
                email_body += f"""
---
This is an automated message from The Hatchery scheduling system.
If you have any questions, please contact your supervisor.
"""
                
                try:
                    # Use Django's send_mail
                    send_mail(
                        subject=email_subject,
                        message=email_body,
                        from_email=from_email,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                    emails_sent += 1
                except Exception as e:
                    email_errors.append(f"{user.email}: {str(e)}")
        
        # Create publication record
        publication = SchedulePublication.objects.create(
            semester=semester,
            published_by=request.user,
            weeks_count=len(weeks),
            recipients_count=len(recipients),
            calendar_invites_sent=calendar_invites_sent > 0,
            email_sent=emails_sent > 0,
            status='sent' if not email_errors else 'partial'
        )
        
        response_data = {
            'success': True,
            'publication_id': publication.id,
            'calendar_invites_sent': calendar_invites_sent,
            'emails_sent': emails_sent,
            'recipients_count': len(recipients),
            'message': f'Successfully published schedule to {emails_sent} recipients'
        }
        
        if email_errors:
            response_data['email_errors'] = email_errors[:5]  # Limit errors shown
            response_data['message'] += f' ({len(email_errors)} email errors)'
        
        return JsonResponse(response_data)
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


# ==========================================
# UTILITY FUNCTIONS
# ==========================================

def get_machine_categories():
    """Get all unique machine categories"""
    from machines.models import Machine
    
    categories = Machine.objects.values_list('category', flat=True).distinct()
    return list(categories)


# ==========================================
# REVIEW REQUESTS
# ==========================================

@login_required
@user_passes_test(is_staff_user)
def api_get_requests(request):
    """Get shift change requests"""
    semester_id = request.GET.get('semester_id')
    
    requests_qs = ShiftChangeRequest.objects.select_related(
        'shift', 'requested_by', 'swap_with_user', 'swap_with_shift', 'reviewed_by'
    ).order_by('-created_at')
    
    if semester_id:
        requests_qs = requests_qs.filter(shift__semester_id=semester_id)
    
    requests_data = []
    for req in requests_qs:
        shift_data = {
            'id': req.shift.id,
            'date': req.shift.date.isoformat(),
            'start_time': req.shift.start_time.strftime('%H:%M'),
            'end_time': req.shift.end_time.strftime('%H:%M'),
            'shift_type': req.shift.shift_type,
        }
        
        swap_shift_data = None
        if req.swap_with_shift:
            swap_shift_data = {
                'id': req.swap_with_shift.id,
                'date': req.swap_with_shift.date.isoformat(),
                'start_time': req.swap_with_shift.start_time.strftime('%H:%M'),
                'end_time': req.swap_with_shift.end_time.strftime('%H:%M'),
                'shift_type': req.swap_with_shift.shift_type,
            }
        
        requests_data.append({
            'id': req.id,
            'request_type': req.request_type,
            'status': req.status,
            'shift': shift_data,
            'requested_by_name': req.requested_by.get_full_name() or req.requested_by.email,
            'swap_with_user_name': req.swap_with_user.get_full_name() if req.swap_with_user else None,
            'swap_with_shift': swap_shift_data,
            'swap_accepted_by_other_user': req.swap_accepted_by_other_user,
            'proposed_date': req.proposed_date.isoformat() if req.proposed_date else None,
            'proposed_start_time': req.proposed_start_time.strftime('%H:%M') if req.proposed_start_time else None,
            'proposed_end_time': req.proposed_end_time.strftime('%H:%M') if req.proposed_end_time else None,
            'cancellation_reason': req.cancellation_reason,
            'admin_notes': req.admin_notes,
            'reviewed_by': req.reviewed_by.get_full_name() if req.reviewed_by else None,
            'reviewed_at': req.reviewed_at.isoformat() if req.reviewed_at else None,
            'created_at': req.created_at.isoformat(),
        })
    
    return JsonResponse({'requests': requests_data})


@login_required
@user_passes_test(is_staff_user)
@require_POST
def api_approve_request(request):
    """Approve a shift change request"""
    try:
        data = json.loads(request.body)
        request_id = data.get('request_id')
        
        change_request = get_object_or_404(ShiftChangeRequest, id=request_id)
        
        if change_request.status != 'pending':
            return JsonResponse({'success': False, 'error': 'Request already processed'})
        
        # Handle based on request type
        if change_request.request_type == 'swap':
            # Swap the shifts between users
            if change_request.swap_with_shift and change_request.swap_with_user:
                original_user = change_request.shift.user
                swap_user = change_request.swap_with_shift.user
                
                # Swap users
                change_request.shift.user = swap_user
                change_request.swap_with_shift.user = original_user
                
                change_request.shift.save()
                change_request.swap_with_shift.save()
        
        elif change_request.request_type == 'amendment':
            # Update the shift with proposed changes
            if change_request.proposed_date:
                change_request.shift.date = change_request.proposed_date
            if change_request.proposed_start_time:
                change_request.shift.start_time = change_request.proposed_start_time
            if change_request.proposed_end_time:
                change_request.shift.end_time = change_request.proposed_end_time
            change_request.shift.save()
        
        elif change_request.request_type == 'cancellation':
            # Delete or mark shift as cancelled
            change_request.shift.status = 'cancelled'
            change_request.shift.save()
        
        # Update request status
        change_request.status = 'approved'
        change_request.reviewed_by = request.user
        change_request.reviewed_at = datetime.now()
        change_request.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff_user)
@require_POST
def api_reject_request(request):
    """Reject a shift change request"""
    try:
        data = json.loads(request.body)
        request_id = data.get('request_id')
        reason = data.get('reason', '')
        
        change_request = get_object_or_404(ShiftChangeRequest, id=request_id)
        
        if change_request.status != 'pending':
            return JsonResponse({'success': False, 'error': 'Request already processed'})
        
        change_request.status = 'rejected'
        change_request.reviewed_by = request.user
        change_request.reviewed_at = datetime.now()
        change_request.admin_notes = reason
        change_request.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})