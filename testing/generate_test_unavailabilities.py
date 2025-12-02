"""
Generate Random Unavailabilities for Test Users
================================================

Creates realistic unavailability patterns for test users:
- Class schedules (MWF or TTh patterns)
- Work commitments
- Personal time blocks
- Some users have lots of availability, others are very busy

Usage:
    python manage.py shell < generate_test_unavailabilities.py
    
Or in Django shell:
    exec(open('generate_test_unavailabilities.py').read())
"""

import random
from datetime import time
from django.contrib.auth import get_user_model
from scheduling.models import TeamMemberProfile, Semester, Unavailability

User = get_user_model()

# Configuration
MIN_BLOCKS_PER_USER = 0  # Some users have full availability
MAX_BLOCKS_PER_USER = 8  # Max unavailability blocks per user

# Common class/work patterns
CLASS_PATTERNS = [
    # MWF morning classes
    {'days': [0, 2, 4], 'start': time(8, 0), 'end': time(10, 0), 'name': 'Morning classes (MWF)'},
    {'days': [0, 2, 4], 'start': time(9, 0), 'end': time(11, 0), 'name': 'Morning classes (MWF)'},
    {'days': [0, 2, 4], 'start': time(10, 0), 'end': time(12, 0), 'name': 'Late morning classes (MWF)'},
    
    # MWF afternoon classes
    {'days': [0, 2, 4], 'start': time(13, 0), 'end': time(15, 0), 'name': 'Afternoon classes (MWF)'},
    {'days': [0, 2, 4], 'start': time(14, 0), 'end': time(16, 0), 'name': 'Afternoon classes (MWF)'},
    {'days': [0, 2, 4], 'start': time(15, 0), 'end': time(17, 0), 'name': 'Late afternoon classes (MWF)'},
    
    # TTh morning classes
    {'days': [1, 3], 'start': time(8, 0), 'end': time(9, 30), 'name': 'Morning classes (TTh)'},
    {'days': [1, 3], 'start': time(9, 30), 'end': time(11, 0), 'name': 'Morning classes (TTh)'},
    {'days': [1, 3], 'start': time(11, 0), 'end': time(12, 30), 'name': 'Late morning classes (TTh)'},
    
    # TTh afternoon classes
    {'days': [1, 3], 'start': time(13, 0), 'end': time(14, 30), 'name': 'Afternoon classes (TTh)'},
    {'days': [1, 3], 'start': time(14, 30), 'end': time(16, 0), 'name': 'Afternoon classes (TTh)'},
    {'days': [1, 3], 'start': time(16, 0), 'end': time(17, 30), 'name': 'Late afternoon classes (TTh)'},
]

# Work patterns
WORK_PATTERNS = [
    # Part-time job patterns
    {'days': [0, 2], 'start': time(17, 0), 'end': time(21, 0), 'name': 'Evening job (Mon/Wed)'},
    {'days': [1, 3], 'start': time(17, 0), 'end': time(21, 0), 'name': 'Evening job (Tue/Thu)'},
    {'days': [4], 'start': time(14, 0), 'end': time(22, 0), 'name': 'Friday job'},
    {'days': [5], 'start': time(9, 0), 'end': time(17, 0), 'name': 'Saturday job'},
    {'days': [5, 6], 'start': time(10, 0), 'end': time(18, 0), 'name': 'Weekend job'},
    {'days': [6], 'start': time(12, 0), 'end': time(20, 0), 'name': 'Sunday job'},
]

# Personal time patterns
PERSONAL_PATTERNS = [
    # Morning person (unavailable evenings)
    {'days': [0, 1, 2, 3, 4], 'start': time(18, 0), 'end': time(22, 0), 'name': 'Evening personal time'},
    
    # Night owl (unavailable mornings)
    {'days': [0, 1, 2, 3, 4], 'start': time(8, 0), 'end': time(11, 0), 'name': 'Morning personal time'},
    
    # Lunch commitments
    {'days': [0, 1, 2, 3, 4], 'start': time(12, 0), 'end': time(13, 0), 'name': 'Lunch break'},
    
    # Religious/club commitments
    {'days': [2], 'start': time(19, 0), 'end': time(21, 0), 'name': 'Wednesday night commitment'},
    {'days': [6], 'start': time(9, 0), 'end': time(12, 0), 'name': 'Sunday morning commitment'},
]

# User availability profiles
AVAILABILITY_PROFILES = [
    {'name': 'Very Available', 'num_blocks': (0, 2), 'weight': 20},
    {'name': 'Somewhat Available', 'num_blocks': (2, 4), 'weight': 35},
    {'name': 'Moderately Busy', 'num_blocks': (4, 6), 'weight': 30},
    {'name': 'Very Busy', 'num_blocks': (6, 10), 'weight': 15},
]


def get_weighted_profile():
    """Get a random availability profile based on weights"""
    total_weight = sum(p['weight'] for p in AVAILABILITY_PROFILES)
    r = random.randint(1, total_weight)
    
    cumulative = 0
    for profile in AVAILABILITY_PROFILES:
        cumulative += profile['weight']
        if r <= cumulative:
            return profile
    
    return AVAILABILITY_PROFILES[0]


def generate_unavailabilities():
    """Generate random unavailabilities for all test users"""
    
    print("=" * 60)
    print("GENERATING UNAVAILABILITIES")
    print("=" * 60)
    
    # Get active semester
    semester = Semester.objects.filter(is_active=True).first()
    if not semester:
        print("❌ No active semester found! Run generate_test_users.py first.")
        return
    
    print(f"\nSemester: {semester.name}")
    
    # Get all test users
    test_users = User.objects.filter(
        email__startswith='test',
        email__endswith='@gmail.com'
    )
    
    if not test_users.exists():
        print("❌ No test users found! Run generate_test_users.py first.")
        return
    
    print(f"Found {test_users.count()} test users")
    
    # Clear existing unavailabilities for test users
    print(f"\n🗑️  Clearing existing unavailabilities...")
    deleted = Unavailability.objects.filter(
        user__in=test_users,
        semester=semester
    ).delete()
    print(f"   Deleted {deleted[0]} unavailability entries")
    
    # All patterns combined
    all_patterns = CLASS_PATTERNS + WORK_PATTERNS + PERSONAL_PATTERNS
    
    # Track statistics
    total_blocks = 0
    profile_counts = {p['name']: 0 for p in AVAILABILITY_PROFILES}
    
    print(f"\n📅 Generating unavailabilities...")
    
    for user in test_users:
        # Get random availability profile
        profile = get_weighted_profile()
        profile_counts[profile['name']] += 1
        
        # Determine number of unavailability blocks
        min_blocks, max_blocks = profile['num_blocks']
        num_blocks = random.randint(min_blocks, max_blocks)
        
        if num_blocks == 0:
            print(f"   ✓ {user.email}: Full availability (0 blocks)")
            continue
        
        # Select random patterns
        selected_patterns = random.sample(all_patterns, min(num_blocks, len(all_patterns)))
        
        # Group by day - only keep one slot per day (the model has unique constraint)
        day_slots = {}  # {day: (start_time, end_time, reason)}
        
        for pattern in selected_patterns:
            for day in pattern['days']:
                # Only keep the first slot for each day (or could merge, but simpler to skip)
                if day not in day_slots:
                    day_slots[day] = (pattern['start'], pattern['end'], pattern['name'])
        
        blocks_created = 0
        for day, (start, end, reason) in day_slots.items():
            Unavailability.objects.create(
                user=user,
                semester=semester,
                day_of_week=day,
                start_time=start,
                end_time=end,
                reason=reason
            )
            blocks_created += 1
            total_blocks += 1
        
        print(f"   ✓ {user.email}: {blocks_created} blocks ({profile['name']})")
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    print(f"\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    print(f"\nTotal unavailability blocks created: {total_blocks}")
    
    print(f"\nUsers by availability profile:")
    for profile_name, count in profile_counts.items():
        print(f"   {profile_name}: {count} users")
    
    # Show breakdown by day
    print(f"\nBlocks by day:")
    for day in range(7):
        day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][day]
        count = Unavailability.objects.filter(
            user__in=test_users,
            semester=semester,
            day_of_week=day
        ).count()
        print(f"   {day_name}: {count} blocks")
    
    print(f"\n✅ Done!")
    
    return total_blocks


def show_user_availability(email):
    """Helper to show a specific user's unavailabilities"""
    user = User.objects.filter(email=email).first()
    if not user:
        print(f"User {email} not found")
        return
    
    semester = Semester.objects.filter(is_active=True).first()
    unavails = Unavailability.objects.filter(user=user, semester=semester).order_by('day_of_week', 'start_time')
    
    print(f"\nUnavailabilities for {user.get_full_name()} ({email}):")
    print("-" * 50)
    
    if not unavails.exists():
        print("   Fully available!")
        return
    
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    current_day = None
    
    for u in unavails:
        if u.day_of_week != current_day:
            current_day = u.day_of_week
            print(f"\n   {day_names[current_day]}:")
        
        print(f"      {u.start_time.strftime('%H:%M')} - {u.end_time.strftime('%H:%M')}: {u.reason}")


def clear_all_unavailabilities():
    """Clear all unavailabilities for test users"""
    semester = Semester.objects.filter(is_active=True).first()
    test_users = User.objects.filter(email__startswith='test', email__endswith='@gmail.com')
    
    deleted = Unavailability.objects.filter(user__in=test_users, semester=semester).delete()
    print(f"Deleted {deleted[0]} unavailability entries")


if __name__ == '__main__':
    generate_unavailabilities()
else:
    # Running in Django shell
    generate_unavailabilities()