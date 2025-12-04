"""
Generate Test Users for The Hatchery
=====================================

Creates 50 test users with:
- Unique emails (test1@gmail.com, test2@gmail.com, etc.)
- Distributed across teams/categories (pulled from database)
- 1 team lead per category
- 80% trainers with team assignments
- 20% regular team members (no training capability)

Usage:
    python manage.py shell < testing/generate_test_users.py
    
Or in Django shell:
    exec(open('testing/generate_test_users.py').read())
"""

import random
from django.contrib.auth import get_user_model
from scheduling.models import TeamMemberProfile, Semester

User = get_user_model()

# Configuration
NUM_USERS = 50
TRAINER_PERCENTAGE = 0.80  # 80% are trainers
TEAM_LEAD_PER_CATEGORY = 1

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


def get_categories_from_database():
    """
    Pull categories from the database.
    Tries multiple sources: MachineCategory model, Machine model, or fallback.
    Returns list of dicts: [{'name': 'Laser Cutting', 'slug': 'laser', 'icon': '⚡'}, ...]
    """
    categories = []
    
    # Try 1: MachineCategory model (if exists)
    try:
        from machines.models import MachineCategory
        db_categories = MachineCategory.objects.filter(is_active=True).order_by('name')
        
        if db_categories.exists():
            print("📦 Loading categories from MachineCategory model...")
            for cat in db_categories:
                categories.append({
                    'id': cat.id,
                    'name': cat.name,
                    'slug': cat.slug if hasattr(cat, 'slug') else cat.name.lower().replace(' ', '_'),
                    'icon': cat.icon if hasattr(cat, 'icon') else '🔧',
                })
            return categories
    except (ImportError, Exception) as e:
        print(f"   MachineCategory not available: {e}")
    
    # Try 2: Get distinct categories from Machine model
    try:
        from machines.models import Machine
        
        # Check if Machine has a category field
        if hasattr(Machine, 'category'):
            distinct_categories = Machine.objects.values_list('category', flat=True).distinct()
            distinct_categories = [c for c in distinct_categories if c]  # Remove None/empty
            
            if distinct_categories:
                print("📦 Loading categories from Machine.category field...")
                
                # Try to get CATEGORY_CHOICES if defined
                category_choices = {}
                if hasattr(Machine, 'CATEGORY_CHOICES'):
                    category_choices = dict(Machine.CATEGORY_CHOICES)
                
                for cat_value in distinct_categories:
                    # Get display name from choices or format the value
                    display_name = category_choices.get(cat_value, cat_value.replace('_', ' ').title())
                    
                    # Assign icons based on category name
                    icon = get_icon_for_category(cat_value)
                    
                    categories.append({
                        'id': cat_value,
                        'name': display_name,
                        'slug': cat_value,
                        'icon': icon,
                    })
                return categories
        
        # Try category as ForeignKey
        if hasattr(Machine, 'category') and hasattr(Machine.category, 'field'):
            field = Machine.category.field
            if hasattr(field, 'related_model'):
                CategoryModel = field.related_model
                print(f"📦 Loading categories from {CategoryModel.__name__}...")
                for cat in CategoryModel.objects.all():
                    categories.append({
                        'id': cat.id,
                        'name': cat.name,
                        'slug': getattr(cat, 'slug', cat.name.lower().replace(' ', '_')),
                        'icon': getattr(cat, 'icon', get_icon_for_category(cat.name)),
                    })
                return categories
                
    except (ImportError, Exception) as e:
        print(f"   Machine model not available: {e}")
    
    # Try 3: Check for Category model directly
    try:
        from machines.models import Category
        db_categories = Category.objects.all().order_by('name')
        
        if db_categories.exists():
            print("📦 Loading categories from Category model...")
            for cat in db_categories:
                categories.append({
                    'id': cat.id,
                    'name': cat.name,
                    'slug': getattr(cat, 'slug', cat.name.lower().replace(' ', '_')),
                    'icon': getattr(cat, 'icon', get_icon_for_category(cat.name)),
                })
            return categories
    except (ImportError, Exception) as e:
        print(f"   Category model not available: {e}")
    
    # Fallback: Use hardcoded categories that match common makerspace setups
    print("⚠️  No categories found in database, using defaults...")
    return [
        {'id': 1, 'name': 'Laser Cutting', 'slug': 'laser', 'icon': '⚡'},
        {'id': 2, 'name': '3D Printing', 'slug': '3d_printing', 'icon': '🖨️'},
        {'id': 3, 'name': 'Woodworking', 'slug': 'woodworking', 'icon': '🪚'},
        {'id': 4, 'name': 'Textiles', 'slug': 'textiles', 'icon': '🧵'},
        {'id': 5, 'name': 'Electronics', 'slug': 'electronics', 'icon': '💡'},
        {'id': 6, 'name': 'Metalworking', 'slug': 'metalworking', 'icon': '⚙️'},
        {'id': 7, 'name': 'Vinyl Cutting', 'slug': 'vinyl', 'icon': '✂️'},
    ]


def get_icon_for_category(category_name):
    """Get an appropriate emoji icon for a category based on its name"""
    name_lower = category_name.lower()
    
    icon_map = {
        'laser': '⚡',
        'cutting': '⚡',
        '3d': '🖨️',
        'print': '🖨️',
        'wood': '🪚',
        'textile': '🧵',
        'sew': '🧵',
        'fabric': '🧵',
        'electron': '💡',
        'circuit': '💡',
        'metal': '⚙️',
        'weld': '⚙️',
        'vinyl': '✂️',
        'cnc': '🔩',
        'mill': '🔩',
        'water': '💧',
        'plasma': '🔥',
    }
    
    for keyword, icon in icon_map.items():
        if keyword in name_lower:
            return icon
    
    return '🔧'  # Default icon


def generate_users():
    """Generate test users and team member profiles"""
    
    print("=" * 60)
    print("GENERATING TEST USERS")
    print("=" * 60)
    
    # =========================================================================
    # STEP 0: Get categories from database
    # =========================================================================
    categories = get_categories_from_database()
    
    print(f"\n📋 Found {len(categories)} categories:")
    for cat in categories:
        print(f"   {cat['icon']} {cat['name']} (slug: {cat['slug']})")
    
    # =========================================================================
    # STEP 1: Get or create active semester
    # =========================================================================
    semester = Semester.objects.filter(is_active=True).first()
    if not semester:
        print("\n⚠️  No active semester found. Creating one...")
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
    else:
        print(f"\n✅ Using active semester: {semester.name}")
    
    # =========================================================================
    # STEP 2: Calculate distribution
    # =========================================================================
    num_team_leads = len(categories) * TEAM_LEAD_PER_CATEGORY
    num_trainers = int((NUM_USERS - num_team_leads) * TRAINER_PERCENTAGE)
    num_members = NUM_USERS - num_team_leads - num_trainers
    
    print(f"\n📊 Planned distribution:")
    print(f"   Team Leads: {num_team_leads} (1 per category)")
    print(f"   Trainers: {num_trainers} (~80% of remaining)")
    print(f"   Regular Members: {num_members} (~20% of remaining)")
    print(f"   Total: {NUM_USERS} users (test3-test{2+NUM_USERS}@gmail.com)")
    print(f"   Note: test1@gmail.com and test2@gmail.com are reserved for demo")
    
    # =========================================================================
    # STEP 3: Clear existing test users (EXCEPT test1 and test2)
    # =========================================================================
    print(f"\n🗑️  Clearing existing test users (preserving test1@gmail.com and test2@gmail.com)...")
    # Only delete test3@gmail.com and above
    test_users = User.objects.filter(
        email__startswith='test',
        email__endswith='@gmail.com'
    ).exclude(email__in=['test1@gmail.com', 'test2@gmail.com'])
    
    # Delete TeamMemberProfiles first
    deleted_profiles = TeamMemberProfile.objects.filter(user__in=test_users).delete()
    print(f"   Deleted {deleted_profiles[0]} team profiles")
    
    # Delete the users
    deleted_users = test_users.delete()
    print(f"   Deleted {deleted_users[0]} users")
    
    # Clean up orphaned profiles
    orphaned = TeamMemberProfile.objects.filter(user__isnull=True).delete()
    if orphaned[0] > 0:
        print(f"   Deleted {orphaned[0]} orphaned profiles")
    
    # Track created users
    created_users = []
    # Start from test3@gmail.com (skip test1 and test2 for demo)
    user_index = 3
    
    # Shuffle names for variety
    random.shuffle(FIRST_NAMES)
    random.shuffle(LAST_NAMES)
    
    # =========================================================================
    # STEP 4: Create Team Leads (1 per category)
    # =========================================================================
    print(f"\n👑 Creating Team Leads...")
    
    for category in categories:
        email = f"test{user_index}@gmail.com"
        first_name = FIRST_NAMES[(user_index - 1) % len(FIRST_NAMES)]
        last_name = LAST_NAMES[(user_index - 1) % len(LAST_NAMES)]
        
        user = User.objects.create_user(
            email=email,
            password='testpass123',
            first_name=first_name,
            last_name=last_name,
            role='Team Member'
        )
        user.is_team_lead = True
        user.is_trainer = True
        user.team_assignment = category['name']  # Use the display name
        user.save()
        
        profile, created = TeamMemberProfile.objects.get_or_create(
            user=user,
            defaults={
                'role': 'team_lead',
                'team': category['name'],
                'is_trainer': True,
                'is_team_lead': True,
                'max_weekly_hours': 15,
                'shift_preference': 'no_preference'
            }
        )
        if not created:
            profile.role = 'team_lead'
            profile.team = category['name']
            profile.is_trainer = True
            profile.is_team_lead = True
            profile.max_weekly_hours = 15
            profile.save()
        
        print(f"   ✓ {email}: {first_name} {last_name} - Team Lead ({category['icon']} {category['name']})")
        created_users.append({
            'user': user, 
            'profile': profile, 
            'role': 'team_lead',
            'category': category
        })
        user_index += 1
    
    # =========================================================================
    # STEP 5: Create Trainers (distributed across categories)
    # =========================================================================
    print(f"\n🎓 Creating Trainers...")
    
    trainers_per_category = num_trainers // len(categories)
    extra_trainers = num_trainers % len(categories)
    
    for i, category in enumerate(categories):
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
                role='Team Member'
            )
            user.is_trainer = True
            user.team_assignment = category['name']
            user.save()
            
            hours = random.choice([5, 8, 10, 12, 15, 20])
            pref = random.choice(['no_preference', 'few_long', 'many_short'])
            
            profile, created = TeamMemberProfile.objects.get_or_create(
                user=user,
                defaults={
                    'role': 'team_member',
                    'team': category['name'],
                    'is_trainer': True,
                    'max_weekly_hours': hours,
                    'shift_preference': pref
                }
            )
            if not created:
                profile.role = 'team_member'
                profile.team = category['name']
                profile.is_trainer = True
                profile.max_weekly_hours = hours
                profile.shift_preference = pref
                profile.save()
            
            print(f"   ✓ {email}: {first_name} {last_name} - Trainer ({category['icon']} {category['name']}, {hours}hrs/wk)")
            created_users.append({
                'user': user, 
                'profile': profile, 
                'role': 'trainer',
                'category': category
            })
            user_index += 1
    
    # =========================================================================
    # STEP 6: Create Regular Team Members (floaters)
    # =========================================================================
    print(f"\n👤 Creating Regular Team Members (non-trainers/floaters)...")
    
    for _ in range(num_members):
        email = f"test{user_index}@gmail.com"
        first_name = FIRST_NAMES[(user_index - 1) % len(FIRST_NAMES)]
        last_name = LAST_NAMES[(user_index - 1) % len(LAST_NAMES)]
        
        user = User.objects.create_user(
            email=email,
            password='testpass123',
            first_name=first_name,
            last_name=last_name,
            role='Team Member'
        )
        
        hours = random.choice([5, 8, 10])
        pref = random.choice(['no_preference', 'few_long', 'many_short'])
        
        profile, created = TeamMemberProfile.objects.get_or_create(
            user=user,
            defaults={
                'role': 'team_member',
                'team': '',
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
        
        print(f"   ✓ {email}: {first_name} {last_name} - Floater ({hours}hrs/wk)")
        created_users.append({
            'user': user, 
            'profile': profile, 
            'role': 'member',
            'category': None
        })
        user_index += 1
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    print(f"\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    # Count by role
    role_counts = {'team_lead': 0, 'trainer': 0, 'member': 0}
    for u in created_users:
        role_counts[u['role']] = role_counts.get(u['role'], 0) + 1
    
    print(f"\n📊 Created {len(created_users)} users:")
    print(f"   👑 Team Leads: {role_counts['team_lead']}")
    print(f"   🎓 Trainers: {role_counts['trainer']}")
    print(f"   👤 Floaters: {role_counts['member']}")
    
    # Count by team/category
    team_counts = {}
    for u in created_users:
        if u['category']:
            key = f"{u['category']['icon']} {u['category']['name']}"
        else:
            key = '🔄 Floater (No Team)'
        team_counts[key] = team_counts.get(key, 0) + 1
    
    print(f"\n📋 By Category:")
    for team, count in sorted(team_counts.items()):
        print(f"   {team}: {count}")
    
    # Total hours capacity
    total_hours = sum(u['profile'].max_weekly_hours for u in created_users)
    print(f"\n⏱️  Total weekly hours capacity: {total_hours} hours")
    
    print(f"\n" + "=" * 60)
    print("✅ DONE!")
    print("=" * 60)
    print(f"\n   All users have password: testpass123")
    print(f"\n   Example logins:")
    print(f"   • test3@gmail.com - Team Lead (first user)")
    print(f"   • test{len(categories) + 3}@gmail.com - Trainer")
    print(f"   • test{user_index - 1}@gmail.com - Last user")
    print(f"\n   Note: test1@gmail.com and test2@gmail.com are reserved for demo")
    
    return created_users


# =========================================================================
# RUN
# =========================================================================
if __name__ == '__main__':
    generate_users()
else:
    # Running in Django shell
    generate_users()