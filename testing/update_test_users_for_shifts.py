"""
Update Test Users to Get Shifts
================================

Updates test1@gmail.com and test2@gmail.com to have proper TeamMemberProfile
settings so they get assigned shifts by the auto-scheduler.

Run with:
    python manage.py shell < testing/update_test_users_for_shifts.py
"""

from django.contrib.auth import get_user_model
from scheduling.models import TeamMemberProfile, Semester

User = get_user_model()


def update_test_users():
    """Update test users to be eligible for shifts."""
    
    print("=" * 60)
    print("UPDATING TEST USERS FOR SHIFTS")
    print("=" * 60)
    
    # Get active semester
    semester = Semester.objects.filter(is_active=True).first()
    if not semester:
        print("\n⚠️  No active semester found!")
        return
    
    print(f"\n📅 Using semester: {semester.name}")
    
    # Update test1@gmail.com
    print("\n👤 Updating test1@gmail.com...")
    try:
        user1 = User.objects.get(email='test1@gmail.com')
        
        profile1, created = TeamMemberProfile.objects.get_or_create(
            user=user1,
            defaults={
                'semester': semester,
                'role': 'team_member',
                'team': '3D Printing',
                'max_weekly_hours': 10,
                'expected_weekly_hours': 8,
                'shift_preference': 'no_preference',
                'is_active': True
            }
        )
        
        # Update existing profile
        profile1.is_active = True
        profile1.semester = semester
        profile1.team = '3D Printing'
        profile1.max_weekly_hours = 10
        profile1.expected_weekly_hours = 8
        profile1.shift_preference = 'no_preference'
        profile1.save()
        
        # Also update User.team_assignment to match
        user1.team_assignment = '3D Printing'
        user1.save()
        
        print(f"   ✓ Updated: test1@gmail.com")
        print(f"      Team: {profile1.team}")
        print(f"      Max hours: {profile1.max_weekly_hours}")
        print(f"      Is active: {profile1.is_active}")
        
    except User.DoesNotExist:
        print("   ❌ ERROR: test1@gmail.com not found!")
        print("   Run: python manage.py shell < testing/generate_demo_users.py")
    
    # Update test2@gmail.com
    print("\n👤 Updating test2@gmail.com...")
    try:
        user2 = User.objects.get(email='test2@gmail.com')
        
        profile2, created = TeamMemberProfile.objects.get_or_create(
            user=user2,
            defaults={
                'semester': semester,
                'role': 'team_member',
                'team': 'Laser',
                'max_weekly_hours': 10,
                'expected_weekly_hours': 8,
                'shift_preference': 'no_preference',
                'is_active': True
            }
        )
        
        # Update existing profile
        profile2.is_active = True
        profile2.semester = semester
        profile2.team = 'Laser'
        profile2.max_weekly_hours = 10
        profile2.expected_weekly_hours = 8
        profile2.shift_preference = 'no_preference'
        profile2.save()
        
        # Also update User.team_assignment to match
        user2.team_assignment = 'Laser'
        user2.save()
        
        print(f"   ✓ Updated: test2@gmail.com")
        print(f"      Team: {profile2.team}")
        print(f"      Max hours: {profile2.max_weekly_hours}")
        print(f"      Is active: {profile2.is_active}")
        
    except User.DoesNotExist:
        print("   ❌ ERROR: test2@gmail.com not found!")
        print("   Run: python manage.py shell < testing/generate_demo_users.py")
    
    # Verify
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    
    active_profiles = TeamMemberProfile.objects.filter(
        is_active=True,
        user__email__in=['test1@gmail.com', 'test2@gmail.com']
    )
    
    print(f"\n✅ Found {active_profiles.count()} active test user profiles:")
    for profile in active_profiles:
        print(f"   - {profile.user.email}: {profile.team} ({profile.max_weekly_hours} hrs/week)")
    
    print("\n" + "=" * 60)
    print("✅ Done! Test users are now eligible for shifts.")
    print("=" * 60)
    print("\n📝 Next step: Run the auto-scheduler to assign shifts.")
    print()


if __name__ == '__main__':
    update_test_users()
else:
    # Running in Django shell
    update_test_users()

