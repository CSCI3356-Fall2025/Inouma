from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, date
import json

User = get_user_model()


def is_staff_user(user):
    """Check if user is staff"""
    return user.is_staff or user.is_superuser

def is_team_member(user):
    """Check if user is a team member, trainer, team lead, or staff"""
    if user.is_staff or user.is_superuser:
        return True
    if user.is_trainer or user.is_team_lead:
        return True
    if hasattr(user, 'role') and user.role == 'Team Member':
        return True
    return False


@login_required
@user_passes_test(is_staff_user)
def team_directory(request):
    """Team directory page"""
    return render(request, 'team/team_directory.html')


@login_required
@user_passes_test(is_staff_user)
def api_get_team_members(request):
    """Get all team members"""
    members = []
    
    try:
        from scheduling.models import TeamMemberProfile, TeamGroup
        from accounts.models import StudentProfile
        
        # Get all Team Member users
        team_member_users = User.objects.filter(role='Team Member', is_active=True)
        
        for user in team_member_users:
            # Get StudentProfile for birthday/grad_year (primary source)
            birthday = None
            grad_year = None
            try:
                student_profile = user.student_profile
                if student_profile.birthday:
                    birthday = student_profile.birthday.isoformat()
                if student_profile.graduation_year:
                    grad_year = student_profile.graduation_year
            except:
                pass
            
            # Get TeamMemberProfile for scheduling data
            phone = ''
            group_id = None
            max_weekly_hours = 20
            min_weekly_hours = 0
            notes = ''
            trained_on = []
            try:
                profile = TeamMemberProfile.objects.get(user=user)
                phone = getattr(profile, 'phone', '') or ''
                group_id = profile.team_group_id if hasattr(profile, 'team_group_id') else None
                max_weekly_hours = profile.max_weekly_hours
                min_weekly_hours = getattr(profile, 'min_weekly_hours', 0)
                notes = getattr(profile, 'notes', '') or ''
                trained_on = getattr(profile, 'trained_on', []) or []
                
                # Fallback to TeamMemberProfile for birthday/grad_year if not in StudentProfile
                if not birthday and getattr(profile, 'birthday', None):
                    birthday = profile.birthday.isoformat()
                if not grad_year and getattr(profile, 'graduation_year', None):
                    grad_year = profile.graduation_year
            except TeamMemberProfile.DoesNotExist:
                pass
            
            # Get trainer profile data
            trainer_specialty = ''
            trainer_bio = ''
            trainer_certifications = ''
            try:
                trainer_profile = user.trainer_profile
                trainer_specialty = trainer_profile.specialty or ''
                trainer_bio = trainer_profile.bio or ''
                trainer_certifications = trainer_profile.certifications or ''
            except:
                pass
            
            members.append({
                'id': str(user.id),  # UUID to string
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'phone': phone,
                'birthday': birthday,
                'grad_year': grad_year,
                'group_id': group_id,
                'is_trainer': user.is_trainer,  # From User model
                'is_lead': user.is_team_lead,   # From User model
                'team_assignment': user.team_assignment,  # From User model
                'max_weekly_hours': max_weekly_hours,
                'min_weekly_hours': min_weekly_hours,
                'notes': notes,
                'profile_image': user.profile_picture.url if user.profile_picture else None,
                'trained_on': trained_on,
                'trainer_specialty': trainer_specialty,
                'trainer_bio': trainer_bio,
                'trainer_certifications': trainer_certifications,
            })
        
        # Also include Staff users
        staff_users = User.objects.filter(role='Staff', is_active=True)
        for user in staff_users:
            members.append({
                'id': str(user.id),
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'phone': '',
                'birthday': None,
                'grad_year': None,
                'group_id': None,
                'is_trainer': False,
                'is_lead': False,
                'team_assignment': '',
                'max_weekly_hours': 40,
                'min_weekly_hours': 0,
                'notes': '',
                'profile_image': user.profile_picture.url if user.profile_picture else None,
                'trained_on': [],
                'trainer_specialty': '',
                'trainer_bio': '',
                'trainer_certifications': '',
            })
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error loading team members: {e}")
    
    return JsonResponse({'members': members})


@login_required
@user_passes_test(is_staff_user)
def api_get_team_groups(request):
    """Get all team groups"""
    groups_data = []
    
    try:
        from scheduling.models import TeamGroup
        
        groups = TeamGroup.objects.all()
        
        for group in groups:
            groups_data.append({
                'id': group.id,
                'name': group.name,
                'description': getattr(group, 'description', '') or '',
                'lead_id': str(group.lead_id) if hasattr(group, 'lead_id') and group.lead_id else None,
                'color': getattr(group, 'color', '#6b7280') or '#6b7280',
            })
    except Exception as e:
        print(f"Error loading team groups: {e}")
    
    return JsonResponse({'groups': groups_data})


@login_required
@user_passes_test(is_staff_user)
def api_get_machine_categories(request):
    """Get all machine categories for team assignment"""
    try:
        # Try to use the new MachineCategory model first
        try:
            from machines.models import MachineCategory
            categories_qs = MachineCategory.objects.filter(is_active=True).order_by('display_order', 'name')
            categories = [
                {
                    'id': cat.id,
                    'name': cat.name,
                    'icon': cat.icon,
                    'color': cat.color,
                }
                for cat in categories_qs
            ]
            return JsonResponse({
                'categories': categories,
                'category_names': [cat['name'] for cat in categories]  # For backwards compatibility
            })
        except ImportError:
            pass
        
        # Fallback: Try CATEGORY_CHOICES from Machine model
        from machines.models import Machine
        if hasattr(Machine, 'CATEGORY_CHOICES'):
            category_names = [choice[0] for choice in Machine.CATEGORY_CHOICES]
        else:
            # Final fallback to hardcoded list
            category_names = [
                'Laser',
                'Vinyl',
                'Woodworking',
                'Textile',
                'Metalworking',
                '3D Printing',
                'Electronics',
            ]
        
        return JsonResponse({
            'categories': [{'name': name} for name in category_names],
            'category_names': category_names
        })
    except Exception as e:
        print(f"Error loading machine categories: {e}")
        # Return hardcoded fallback
        fallback = ['Laser', 'Vinyl', 'Woodworking', 'Textile', 'Metalworking', '3D Printing', 'Electronics']
        return JsonResponse({
            'categories': [{'name': name} for name in fallback],
            'category_names': fallback
        })


@login_required
@user_passes_test(is_staff_user)
@require_POST
def api_save_team_member(request):
    """Save team member details"""
    try:
        from scheduling.models import TeamMemberProfile
        
        data = json.loads(request.body)
        user_id = data.get('id')
        
        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            # Create new user
            email = data.get('email')
            if not email:
                return JsonResponse({'success': False, 'error': 'Email is required'})
            
            if User.objects.filter(email=email).exists():
                return JsonResponse({'success': False, 'error': 'User with this email already exists'})
            
            user = User.objects.create_user(
                email=email,
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
                role='Team Member'  # Default to Team Member
            )
        
        # Update user basic info
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        
        # Update Team Member specific fields on User model
        user.is_trainer = data.get('is_trainer', False)
        user.is_team_lead = data.get('is_lead', False)
        user.team_assignment = data.get('team_assignment', '')
        
        user.save()
        
        # Get or create scheduling profile for additional fields
        profile, created = TeamMemberProfile.objects.get_or_create(user=user)
        
        # Sync with User model flags
        profile.is_trainer = user.is_trainer
        profile.is_team_lead = user.is_team_lead
        profile.team = user.team_assignment
        
        profile.max_weekly_hours = data.get('max_weekly_hours', 20)
        
        # Optional fields
        if hasattr(profile, 'min_weekly_hours'):
            profile.min_weekly_hours = data.get('min_weekly_hours', 0)
        if hasattr(profile, 'phone'):
            profile.phone = data.get('phone', '')
        if hasattr(profile, 'birthday') and data.get('birthday'):
            try:
                profile.birthday = datetime.strptime(data['birthday'], '%Y-%m-%d').date()
            except:
                pass
        if hasattr(profile, 'graduation_year'):
            grad_year = data.get('grad_year')
            profile.graduation_year = int(grad_year) if grad_year else None
        if hasattr(profile, 'team_group_id'):
            group_id = data.get('group_id')
            profile.team_group_id = int(group_id) if group_id else None
        if hasattr(profile, 'notes'):
            profile.notes = data.get('notes', '')
        
        profile.save()
        
        return JsonResponse({'success': True, 'id': str(user.id)})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff_user)
@require_POST
def api_send_birthday_emails(request):
    """Send birthday emails to team members with birthdays today"""
    try:
        from scheduling.models import TeamMemberProfile
        
        today = date.today()
        emails_sent = 0
        
        # Find members with birthdays today
        profiles_with_birthdays = TeamMemberProfile.objects.filter(
            birthday__month=today.month,
            birthday__day=today.day
        ).select_related('user')
        
        for profile in profiles_with_birthdays:
            user = profile.user
            
            email_body = f"""Happy Birthday, {user.first_name}! 🎂

The entire Hatchery team wishes you a wonderful birthday filled with joy and celebration!

Thank you for being an amazing part of our team.

Best wishes,
The Hatchery Team
"""
            
            try:
                send_mail(
                    subject='🎂 Happy Birthday from The Hatchery!',
                    message=email_body,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'hatchery@bc.edu'),
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                emails_sent += 1
            except Exception as e:
                print(f"Failed to send birthday email to {user.email}: {e}")
        
        return JsonResponse({
            'success': True,
            'emails_sent': emails_sent,
            'message': f'Sent {emails_sent} birthday email(s)'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff_user)
@require_POST
def api_bulk_assign_group(request):
    """Bulk assign team members to a group"""
    try:
        from scheduling.models import TeamMemberProfile
        
        data = json.loads(request.body)
        member_ids = data.get('member_ids', [])
        group_id = data.get('group_id')  # Can be None to remove from group
        
        if not member_ids:
            return JsonResponse({'success': False, 'error': 'No members selected'})
        
        updated_count = 0
        
        for member_id in member_ids:
            try:
                profile = TeamMemberProfile.objects.get(user_id=member_id)
                if hasattr(profile, 'team_group_id'):
                    profile.team_group_id = group_id
                    profile.save()
                    updated_count += 1
            except TeamMemberProfile.DoesNotExist:
                # Create profile if it doesn't exist
                user = User.objects.filter(id=member_id).first()
                if user:
                    profile = TeamMemberProfile.objects.create(
                        user=user,
                        team_group_id=group_id
                    )
                    updated_count += 1
        
        return JsonResponse({
            'success': True,
            'updated_count': updated_count,
            'message': f'Updated {updated_count} member(s)'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff_user)
@require_POST
def api_bulk_team_assign(request):
    """Bulk assign team members to a team (machine category)"""
    try:
        data = json.loads(request.body)
        member_ids = data.get('member_ids', [])
        team_assignment = data.get('team_assignment', '')
        
        if not member_ids:
            return JsonResponse({'success': False, 'error': 'No members selected'})
        
        updated_count = 0
        
        for member_id in member_ids:
            try:
                user = User.objects.get(id=member_id)
                if user.role == 'Team Member':
                    user.team_assignment = team_assignment
                    user.save()
                    updated_count += 1
            except User.DoesNotExist:
                pass
        
        return JsonResponse({
            'success': True,
            'updated_count': updated_count,
            'message': f'Updated {updated_count} member(s)'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff_user)
@require_POST
def api_update_member_group(request):
    """Update a single member's group"""
    try:
        from scheduling.models import TeamMemberProfile
        
        data = json.loads(request.body)
        member_id = data.get('member_id')
        group_id = data.get('group_id')
        
        if not member_id:
            return JsonResponse({'success': False, 'error': 'No member specified'})
        
        try:
            profile = TeamMemberProfile.objects.get(user_id=member_id)
            if hasattr(profile, 'team_group_id'):
                profile.team_group_id = int(group_id) if group_id else None
                profile.save()
        except TeamMemberProfile.DoesNotExist:
            user = User.objects.filter(id=member_id).first()
            if user:
                profile = TeamMemberProfile.objects.create(
                    user=user,
                    team_group_id=int(group_id) if group_id else None
                )
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff_user)
@require_POST
def api_create_member(request):
    """Create a new team member"""
    try:
        data = json.loads(request.body)
        
        # Check if email already exists
        email = data.get('email', '').strip()
        if not email:
            return JsonResponse({'success': False, 'error': 'Email is required'})
        
        if User.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'error': 'A user with this email already exists'})
        
        # Validate team lead must have team assignment
        is_lead = data.get('is_lead', False)
        team_assignment = data.get('team_assignment', '')
        if is_lead and not team_assignment:
            return JsonResponse({'success': False, 'error': 'Team Leads must be assigned to a team'})
        
        # Parse birthday
        birthday = None
        if data.get('birthday'):
            try:
                birthday = datetime.strptime(data['birthday'], '%Y-%m-%d').date()
            except:
                pass
        
        # Parse grad year
        grad_year = None
        if data.get('grad_year'):
            try:
                grad_year = int(data['grad_year'])
            except:
                pass
        
        # Create the user
        user = User.objects.create(
            email=email,
            first_name=data.get('first_name', '').strip(),
            last_name=data.get('last_name', '').strip(),
            role='Team Member',
            is_trainer=data.get('is_trainer', False),
            is_team_lead=is_lead,
            team_assignment=team_assignment,
        )
        
        # Create StudentProfile for personal info (birthday, grad year)
        try:
            from accounts.models import StudentProfile
            StudentProfile.objects.create(
                user=user,
                birthday=birthday,
                graduation_year=grad_year,
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error creating StudentProfile: {e}")
        
        # Create TeamMemberProfile for scheduling data
        try:
            from scheduling.models import TeamMemberProfile
            TeamMemberProfile.objects.create(
                user=user,
                phone=data.get('phone', ''),
                max_weekly_hours=data.get('max_weekly_hours', 20) or 20,
                min_weekly_hours=data.get('min_weekly_hours', 0) or 0,
                notes=data.get('notes', ''),
                is_trainer=data.get('is_trainer', False),
                is_team_lead=is_lead,
                team=team_assignment,
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error creating TeamMemberProfile: {e}")
        
        # Create TrainerProfile if trainer or lead
        if data.get('is_trainer') or is_lead:
            try:
                from accounts.models import TrainerProfile
                TrainerProfile.objects.create(
                    user=user,
                    specialty=data.get('trainer_specialty', ''),
                    bio=data.get('trainer_bio', ''),
                    certifications=data.get('trainer_certifications', ''),
                )
            except Exception as e:
                print(f"Error creating TrainerProfile: {e}")
        
        return JsonResponse({'success': True, 'member_id': str(user.id)})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff_user)
@require_POST
def api_archive_members(request):
    """Archive (deactivate) team members"""
    try:
        data = json.loads(request.body)
        member_ids = data.get('member_ids', [])
        
        if not member_ids:
            return JsonResponse({'success': False, 'error': 'No members selected'})
        
        archived_count = 0
        for member_id in member_ids:
            try:
                user = User.objects.get(id=member_id)
                user.is_active = False
                user.save()
                archived_count += 1
            except User.DoesNotExist:
                pass
        
        return JsonResponse({
            'success': True,
            'archived_count': archived_count,
            'message': f'Archived {archived_count} member(s)'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff_user)
@require_POST
def api_delete_members(request):
    """Permanently delete team members"""
    try:
        data = json.loads(request.body)
        member_ids = data.get('member_ids', [])
        
        if not member_ids:
            return JsonResponse({'success': False, 'error': 'No members selected'})
        
        deleted_count = 0
        for member_id in member_ids:
            try:
                user = User.objects.get(id=member_id)
                # Delete related profiles first
                try:
                    from scheduling.models import TeamMemberProfile
                    TeamMemberProfile.objects.filter(user=user).delete()
                except:
                    pass
                try:
                    from accounts.models import TrainerProfile
                    TrainerProfile.objects.filter(user=user).delete()
                except:
                    pass
                user.delete()
                deleted_count += 1
            except User.DoesNotExist:
                pass
        
        return JsonResponse({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Deleted {deleted_count} member(s)'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff_user)
@require_POST
def api_update_member(request, member_id):
    """Update an existing team member"""
    try:
        data = json.loads(request.body)
        
        user = User.objects.get(id=member_id)
        
        # Validate team lead must have team assignment
        is_lead = data.get('is_lead', user.is_team_lead)
        team_assignment = data.get('team_assignment', user.team_assignment)
        if is_lead and not team_assignment:
            return JsonResponse({'success': False, 'error': 'Team Leads must be assigned to a team'})
        
        # Update user fields
        user.first_name = data.get('first_name', user.first_name).strip()
        user.last_name = data.get('last_name', user.last_name).strip()
        
        # Check email uniqueness if changed
        new_email = data.get('email', '').strip()
        if new_email and new_email != user.email:
            if User.objects.filter(email=new_email).exclude(id=member_id).exists():
                return JsonResponse({'success': False, 'error': 'A user with this email already exists'})
            user.email = new_email
        
        user.is_trainer = data.get('is_trainer', user.is_trainer)
        user.is_team_lead = is_lead
        user.team_assignment = team_assignment
        user.save()
        
        # Update StudentProfile for personal info (birthday, grad year)
        try:
            from accounts.models import StudentProfile
            student_profile, created = StudentProfile.objects.get_or_create(user=user)
            
            if data.get('birthday'):
                student_profile.birthday = datetime.strptime(data['birthday'], '%Y-%m-%d').date()
            elif 'birthday' in data and data['birthday'] is None:
                student_profile.birthday = None
                
            if data.get('grad_year'):
                student_profile.graduation_year = int(data['grad_year'])
            elif 'grad_year' in data and data['grad_year'] is None:
                student_profile.graduation_year = None
            
            student_profile.save()
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error updating StudentProfile: {e}")
        
        # Update TeamMemberProfile for scheduling data
        try:
            from scheduling.models import TeamMemberProfile
            
            profile, created = TeamMemberProfile.objects.get_or_create(user=user)
            
            profile.phone = data.get('phone', profile.phone or '')
            profile.max_weekly_hours = data.get('max_weekly_hours', profile.max_weekly_hours)
            profile.min_weekly_hours = data.get('min_weekly_hours', profile.min_weekly_hours)
            profile.notes = data.get('notes', profile.notes or '')
            profile.is_trainer = data.get('is_trainer', profile.is_trainer)
            profile.is_team_lead = is_lead
            profile.team = team_assignment
            profile.save()
        except Exception as e:
            print(f"Error updating TeamMemberProfile: {e}")
        
        # Update TrainerProfile
        if data.get('is_trainer') or is_lead:
            try:
                from accounts.models import TrainerProfile
                trainer_profile, created = TrainerProfile.objects.get_or_create(user=user)
                trainer_profile.specialty = data.get('trainer_specialty', trainer_profile.specialty or '')
                trainer_profile.bio = data.get('trainer_bio', trainer_profile.bio or '')
                trainer_profile.certifications = data.get('trainer_certifications', trainer_profile.certifications or '')
                trainer_profile.save()
            except Exception as e:
                print(f"Error updating TrainerProfile: {e}")
        
        return JsonResponse({'success': True})
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Member not found'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})
    


@login_required
@user_passes_test(is_team_member)
def team_dashboard(request):
    """
    Team member dashboard - renders trainerDashboard.html
    Accessible to team members, trainers, team leads, and staff.
    """
    from scheduling.models import Semester, Shift, Unavailability
    
    context = {}
    
    # Get active semester
    try:
        active_semester = Semester.objects.filter(is_active=True).first()
        context['active_semester'] = active_semester
    except:
        context['active_semester'] = None
    
    # Get upcoming shifts
    try:
        today = date.today()
        upcoming_shifts = Shift.objects.filter(
            user=request.user,
            date__gte=today,
            status__in=['scheduled', 'published']
        ).order_by('date', 'start_time')[:5]
        context['upcoming_shifts'] = list(upcoming_shifts)
    except Exception as e:
        print(f"Error loading shifts: {e}")
        context['upcoming_shifts'] = []
    
    # Get unavailability blocks
    try:
        if context.get('active_semester'):
            unavailability_blocks = Unavailability.objects.filter(
                user=request.user,
                semester=context['active_semester']
            ).order_by('day_of_week', 'start_time')
            context['unavailability_blocks'] = list(unavailability_blocks)
        else:
            context['unavailability_blocks'] = []
    except Exception as e:
        print(f"Error loading unavailability: {e}")
        context['unavailability_blocks'] = []
    
    return render(request, 'trainerDashboard.html', context)



@login_required
@user_passes_test(is_team_member)
def my_training_sessions(request):
    """
    View for trainers to see their upcoming and past training sessions.
    """
    from reservations.models import TrainingSession
    
    today = date.today()
    
    # Get upcoming sessions
    try:
        upcoming_sessions = TrainingSession.objects.filter(
            trainer=request.user,
            date__gte=today
        ).select_related('training').order_by('date', 'start_time')
    except:
        upcoming_sessions = []
    
    # Get past sessions (last 30 days)
    try:
        past_cutoff = today - timedelta(days=30)
        past_sessions = TrainingSession.objects.filter(
            trainer=request.user,
            date__lt=today,
            date__gte=past_cutoff
        ).select_related('training').order_by('-date', '-start_time')
    except:
        past_sessions = []
    
    context = {
        'upcoming_sessions': upcoming_sessions,
        'past_sessions': past_sessions,
    }
    
    return render(request, 'team/my_training_sessions.html', context)