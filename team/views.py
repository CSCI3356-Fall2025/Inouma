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
        from scheduling.models import TeamMemberProfile
        
        # Get all users with team member profiles
        profiles = TeamMemberProfile.objects.select_related('user', 'team_group').all()
        
        for profile in profiles:
            user = profile.user
            members.append({
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'phone': getattr(profile, 'phone', '') or '',
                'birthday': profile.birthday.isoformat() if getattr(profile, 'birthday', None) else None,
                'grad_year': getattr(profile, 'graduation_year', None),
                'group_id': profile.team_group_id if hasattr(profile, 'team_group_id') else None,
                'is_trainer': profile.is_trainer,
                'is_lead': getattr(profile, 'is_team_lead', False),
                'max_weekly_hours': profile.max_weekly_hours,
                'min_weekly_hours': getattr(profile, 'min_weekly_hours', 0),
                'notes': getattr(profile, 'notes', '') or '',
                'profile_image': getattr(profile, 'profile_image_url', None),
                'trained_on': getattr(profile, 'trained_on', []) or [],
            })
        
        # Also get staff users without profiles
        profiled_user_ids = [p.user_id for p in profiles]
        staff_users = User.objects.filter(is_staff=True, is_active=True).exclude(id__in=profiled_user_ids)
        
        for user in staff_users:
            members.append({
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'phone': '',
                'birthday': None,
                'grad_year': None,
                'group_id': None,
                'is_trainer': False,
                'is_lead': False,
                'max_weekly_hours': 20,
                'min_weekly_hours': 0,
                'notes': '',
                'profile_image': None,
                'trained_on': [],
            })
    except Exception as e:
        print(f"Error loading team members: {e}")
        # Fallback: return all staff users
        staff_users = User.objects.filter(is_staff=True, is_active=True)
        for user in staff_users:
            members.append({
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'phone': '',
                'birthday': None,
                'grad_year': None,
                'group_id': None,
                'is_trainer': False,
                'is_lead': False,
                'max_weekly_hours': 20,
                'min_weekly_hours': 0,
                'notes': '',
                'profile_image': None,
                'trained_on': [],
            })
    
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
                'lead_id': group.lead_id if hasattr(group, 'lead_id') else None,
                'color': getattr(group, 'color', '#6b7280') or '#6b7280',
            })
    except Exception as e:
        print(f"Error loading team groups: {e}")
    
    return JsonResponse({'groups': groups_data})


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
                username=email,
                email=email,
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
                is_staff=True  # Make them staff so they appear in directory
            )
        
        # Update user basic info
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.save()
        
        # Get or create profile
        profile, created = TeamMemberProfile.objects.get_or_create(user=user)
        
        # Update profile
        profile.is_trainer = data.get('is_trainer', False)
        
        if hasattr(profile, 'is_team_lead'):
            profile.is_team_lead = data.get('is_lead', False)
        
        profile.max_weekly_hours = data.get('max_weekly_hours', 20)
        
        # Optional fields (may not exist on model)
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
        
        return JsonResponse({'success': True, 'id': user.id})
        
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