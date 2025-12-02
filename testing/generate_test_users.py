"""
Generate Test Users for The Hatchery
=====================================

Creates 50 test users with:
- Unique emails (test1@gmail.com, test2@gmail.com, etc.)
- Distributed across teams/categories
- 1 team lead per category
- 80% trainers with team assignments
- 20% regular team members (no training capability)

Usage:
    python manage.py shell < generate_test_users.py
    
Or in Django shell:
    exec(open('generate_test_users.py').read())
"""

import random
from django.contrib.auth import get_user_model
from scheduling.models import TeamMemberProfile, Semester

User = get_user_model()

# Configuration
NUM_USERS = 50
TRAINER_PERCENTAGE = 0.80  # 80% are trainers
TEAM_LEAD_PER_CATEGORY = 1

# Machine categories (teams)
CATEGORIES = [
    'laser',
    '3d_printing', 
    'woodworking',
    'textiles',
    'electronics',
    'metalworking',
]

# First names for variety
FIRST_NAMES = [
    'Alex', 'Jordan', 'Taylor', 'Morgan', 'Casey', 'Riley', 'Quinn', 'Avery',
    'Parker', 'Sage', 'Drew', 'Blake', 'Cameron', 'Dakota', 'Emerson', 'Finley',
    'Gray', 'Harper', 'Indigo', 'Jamie', 'Kendall', 'Logan', 'Marley', 'Noah',
    'Oakley', 'Peyton', 'Reagan', 'Reese', 'River', 'Rowan', 'Sawyer', 'Skyler',
    'Spencer', 'Sydney', 'Tatum', 'Teagan', 'Tristan', 'Winter', 'Zion', 'Addison',
    'Ainsley', 'Amari', 'Arden', 'Armani', 'Ashton', 'Bailey', 'Blair', 'Bobbie',
    'Brett', 'Brooklyn'
]

LAST_NAMES = [
    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
    'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
    'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Perez', 'Thompson',
    'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson', 'Walker',
    'Young', 'Allen', 'King', 'Wright', 'Scott', 'Torres', 'Nguyen', 'Hill', 'Flores',
    'Green', 'Adams', 'Nelson', 'Baker', 'Hall', 'Rivera', 'Campbell', 'Mitchell', 'Carter'
]


def generate_users():
    """Generate test users and team member profiles"""
    
    print("=" * 60)
    print("GENERATING TEST USERS")
    print("=" * 60)
    
    # Get or create active semester
    semester = Semester.objects.filter(is_active=True).first()
    if not semester:
        print("⚠️  No active semester found. Creating one...")
        from datetime import date, timedelta
        today = date.today()
        semester = Semester.objects.create(
            name='Test Semester',
            semester_type='fall',
            year=today.year,
            start_date=today,
            end_date=today + timedelta(days=120),
            is_active=True
        )
        print(f"   Created: {semester.name}")
    
    # Calculate distribution
    num_team_leads = len(CATEGORIES) * TEAM_LEAD_PER_CATEGORY  # 6 team leads
    num_trainers = int((NUM_USERS - num_team_leads) * TRAINER_PERCENTAGE)  # ~35 trainers
    num_members = NUM_USERS - num_team_leads - num_trainers  # ~9 regular members
    
    print(f"\nPlanned distribution:")
    print(f"   Team Leads: {num_team_leads} (1 per category)")
    print(f"   Trainers: {num_trainers} (~80% of remaining)")
    print(f"   Regular Members: {num_members} (~20% of remaining)")
    print(f"   Total: {NUM_USERS}")
    
    # Clear existing test users (optional - comment out to keep existing)
    print(f"\n🗑️  Clearing existing test users...")
    test_users = User.objects.filter(email__startswith='test', email__endswith='@gmail.com')
    
    # Delete TeamMemberProfiles first (in case cascade doesn't work)
    deleted_profiles = TeamMemberProfile.objects.filter(user__in=test_users).delete()
    print(f"   Deleted {deleted_profiles[0]} team profiles")
    
    # Now delete the users
    deleted_users = test_users.delete()
    print(f"   Deleted {deleted_users[0]} users")
    
    # Also clean up any orphaned TeamMemberProfiles (profiles without users)
    orphaned = TeamMemberProfile.objects.filter(user__isnull=True).delete()
    print(f"   Deleted {orphaned[0]} orphaned profiles")
    
    # Delete ALL TeamMemberProfiles for test emails that might still exist
    # (the user might have been recreated with a new ID)
    remaining_profiles = TeamMemberProfile.objects.filter(
        user__email__startswith='test', 
        user__email__endswith='@gmail.com'
    ).delete()
    print(f"   Deleted {remaining_profiles[0]} remaining test profiles")
    
    # Track created users
    created_users = []
    user_index = 1
    
    # Shuffle names for variety
    random.shuffle(FIRST_NAMES)
    random.shuffle(LAST_NAMES)
    
    # =========================================================================
    # STEP 1: Create Team Leads (1 per category)
    # =========================================================================
    print(f"\n👑 Creating Team Leads...")
    
    for category in CATEGORIES:
        email = f"test{user_index}@gmail.com"
        first_name = FIRST_NAMES[(user_index - 1) % len(FIRST_NAMES)]
        last_name = LAST_NAMES[(user_index - 1) % len(LAST_NAMES)]
        
        user = User.objects.create_user(
            email=email,
            password='testpass123',
            first_name=first_name,
            last_name=last_name,
            role='Team Member'  # Required for frontend visibility
        )
        # Set team lead and trainer flags
        user.is_team_lead = True
        user.is_trainer = True
        user.team_assignment = category
        user.save()
        
        # Use get_or_create in case a signal created the profile
        profile, created = TeamMemberProfile.objects.get_or_create(
            user=user,
            defaults={
                'role': 'team_lead',
                'team': category,
                'is_trainer': True,
                'is_team_lead': True,
                'max_weekly_hours': 15,
                'shift_preference': 'no_preference'
            }
        )
        if not created:
            # Update existing profile
            profile.role = 'team_lead'
            profile.team = category
            profile.is_trainer = True
            profile.is_team_lead = True
            profile.max_weekly_hours = 15
            profile.shift_preference = 'no_preference'
            profile.save()
        
        print(f"   ✓ {email}: {first_name} {last_name} - Team Lead ({category})")
        created_users.append({'user': user, 'profile': profile, 'role': 'team_lead'})
        user_index += 1
    
    # =========================================================================
    # STEP 2: Create Trainers (distributed across categories)
    # =========================================================================
    print(f"\n🎓 Creating Trainers...")
    
    trainers_per_category = num_trainers // len(CATEGORIES)
    extra_trainers = num_trainers % len(CATEGORIES)
    
    for i, category in enumerate(CATEGORIES):
        # Some categories get an extra trainer to use up the remainder
        count = trainers_per_category + (1 if i < extra_trainers else 0)
        
        for _ in range(count):
            email = f"test{user_index}@gmail.com"
            first_name = FIRST_NAMES[(user_index - 1) % len(FIRST_NAMES)]
            last_name = LAST_NAMES[(user_index - 1) % len(LAST_NAMES)]
            
            user = User.objects.create_user(
                email=email,
                password='testpass123',
                first_name=first_name,
                last_name=last_name,
                role='Team Member'  # Required for frontend visibility
            )
            # Set trainer flag
            user.is_trainer = True
            user.team_assignment = category
            user.save()
            
            # Random hours between 5-20
            hours = random.choice([5, 8, 10, 12, 15, 20])
            pref = random.choice(['no_preference', 'few_long', 'many_short'])
            
            # Use get_or_create in case a signal created the profile
            profile, created = TeamMemberProfile.objects.get_or_create(
                user=user,
                defaults={
                    'role': 'team_member',
                    'team': category,
                    'is_trainer': True,
                    'max_weekly_hours': hours,
                    'shift_preference': pref
                }
            )
            if not created:
                profile.role = 'team_member'
                profile.team = category
                profile.is_trainer = True
                profile.max_weekly_hours = hours
                profile.shift_preference = pref
                profile.save()
            
            print(f"   ✓ {email}: {first_name} {last_name} - Trainer ({category}, {hours}hrs/wk)")
            created_users.append({'user': user, 'profile': profile, 'role': 'trainer'})
            user_index += 1
    
    # =========================================================================
    # STEP 3: Create Regular Team Members (no training, floaters)
    # =========================================================================
    print(f"\n👤 Creating Regular Team Members (non-trainers)...")
    
    for _ in range(num_members):
        email = f"test{user_index}@gmail.com"
        first_name = FIRST_NAMES[(user_index - 1) % len(FIRST_NAMES)]
        last_name = LAST_NAMES[(user_index - 1) % len(LAST_NAMES)]
        
        user = User.objects.create_user(
            email=email,
            password='testpass123',
            first_name=first_name,
            last_name=last_name,
            role='Team Member'  # Required for frontend visibility
        )
        
        # Regular members work fewer hours typically
        hours = random.choice([5, 8, 10])
        pref = random.choice(['no_preference', 'few_long', 'many_short'])
        
        # Use get_or_create in case a signal created the profile
        profile, created = TeamMemberProfile.objects.get_or_create(
            user=user,
            defaults={
                'role': 'team_member',
                'team': '',  # No team - they're floaters
                'is_trainer': False,
                'max_weekly_hours': hours,
                'shift_preference': pref
            }
        )
        if not created:
            profile.role = 'team_member'
            profile.team = ''
            profile.is_trainer = False
            profile.max_weekly_hours = hours
            profile.shift_preference = pref
            profile.save()
        
        print(f"   ✓ {email}: {first_name} {last_name} - Member (floater, {hours}hrs/wk)")
        created_users.append({'user': user, 'profile': profile, 'role': 'member'})
        user_index += 1
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    print(f"\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    # Count by role
    role_counts = {}
    for u in created_users:
        role = u['role']
        role_counts[role] = role_counts.get(role, 0) + 1
    
    print(f"\nCreated {len(created_users)} users:")
    for role, count in role_counts.items():
        print(f"   {role}: {count}")
    
    # Count by team
    team_counts = {}
    for u in created_users:
        team = u['profile'].team or 'No Team (Floater)'
        team_counts[team] = team_counts.get(team, 0) + 1
    
    print(f"\nBy team:")
    for team, count in sorted(team_counts.items()):
        print(f"   {team}: {count}")
    
    # Total hours capacity
    total_hours = sum(u['profile'].max_weekly_hours for u in created_users)
    print(f"\nTotal weekly hours capacity: {total_hours} hours")
    
    print(f"\n✅ Done! All users have password: testpass123")
    print(f"   Login as test1@gmail.com to test team lead features")
    print(f"   Login as test7@gmail.com to test trainer features")
    print(f"   Login as test{user_index-1}@gmail.com to test member features")
    
    return created_users


if __name__ == '__main__':
    generate_users()
else:
    # Running in Django shell
    generate_users()