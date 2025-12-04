"""
Generate Demo Users (Just 2 Users)
==================================

Creates only 2 test users for demo purposes:
- test1@gmail.com: User with NO certifications (for use cases 1 & 4)
- test2@gmail.com: User with certifications (for use cases 2 & 3)

Run with:
    python manage.py shell < testing/generate_demo_users.py
"""

from django.contrib.auth import get_user_model
from scheduling.models import TeamMemberProfile, Semester
from datetime import date, timedelta

User = get_user_model()


def generate_demo_users():
    """Generate only 2 demo users."""
    
    print("=" * 60)
    print("GENERATING DEMO USERS (2 USERS ONLY)")
    print("=" * 60)
    
    # Get or create active semester
    semester = Semester.objects.filter(is_active=True).first()
    if not semester:
        print("\n⚠️  No active semester found. Creating one...")
        today = date.today()
        semester = Semester.objects.create(
            name='Demo Semester',
            semester_type='fall',
            year=today.year,
            start_date=today,
            end_date=today + timedelta(days=120),
            is_active=True
        )
        print(f"   ✓ Created: {semester.name}")
    
    # Clear existing test users
    print("\n🗑️  Clearing existing test users...")
    test_users = User.objects.filter(email__in=['test1@gmail.com', 'test2@gmail.com'])
    
    # Delete TeamMemberProfiles first
    deleted_profiles = TeamMemberProfile.objects.filter(user__in=test_users).delete()
    print(f"   Deleted {deleted_profiles[0]} team profiles")
    
    # Delete the users
    deleted_users = test_users.delete()
    print(f"   Deleted {deleted_users[0]} users")
    
    # =========================================================================
    # Create test1@gmail.com (User with NO certifications)
    # =========================================================================
    print("\n👤 Creating test1@gmail.com (user with NO training)...")
    
    user1 = User.objects.create_user(
        email='test1@gmail.com',
        password='testpass123',
        first_name='Test',
        last_name='User One',
        role='Team Member'
    )
    # Make them a trainer so they can lead training sessions
    user1.is_trainer = True
    user1.is_team_lead = False
    user1.team_assignment = '3D Printing'  # Match the profile team
    user1.save()
    
    # Create basic profile (not required but good for consistency)
    profile1, _ = TeamMemberProfile.objects.get_or_create(
        user=user1,
        defaults={
            'semester': semester,
            'role': 'team_member',
            'team': '3D Printing',  # Assign to a team so they get shifts
            'max_weekly_hours': 10,
            'expected_weekly_hours': 8,
            'shift_preference': 'no_preference',
            'is_active': True  # Must be active to be included in scheduler
        }
    )
    # Ensure is_active is True and is_trainer is True
    profile1.is_active = True
    profile1.is_trainer = True  # Make them a trainer
    profile1.semester = semester
    profile1.team = '3D Printing'  # Assign to a team
    profile1.expected_weekly_hours = 8
    profile1.max_weekly_hours = 10
    profile1.save()
    
    print(f"   ✓ Created: test1@gmail.com")
    print(f"      Name: {user1.first_name} {user1.last_name}")
    print(f"      Role: Regular user (no certifications)")
    
    # =========================================================================
    # Create test2@gmail.com (User WITH certifications)
    # =========================================================================
    print("\n👤 Creating test2@gmail.com (user WITH training)...")
    
    user2 = User.objects.create_user(
        email='test2@gmail.com',
        password='testpass123',
        first_name='Test',
        last_name='User Two',
        role='Team Member'
    )
    # Make them a trainer so they can lead training sessions
    user2.is_trainer = True
    user2.is_team_lead = False
    user2.team_assignment = 'Laser'  # Match the profile team
    user2.save()
    
    # Create basic profile
    profile2, _ = TeamMemberProfile.objects.get_or_create(
        user=user2,
        defaults={
            'semester': semester,
            'role': 'team_member',
            'team': 'Laser',  # Assign to a different team
            'max_weekly_hours': 10,
            'expected_weekly_hours': 8,
            'shift_preference': 'no_preference',
            'is_active': True  # Must be active to be included in scheduler
        }
    )
    # Ensure is_active is True and is_trainer is True
    profile2.is_active = True
    profile2.is_trainer = True  # Make them a trainer
    profile2.semester = semester
    profile2.team = 'Laser'  # Assign to a different team
    profile2.expected_weekly_hours = 8
    profile2.max_weekly_hours = 10
    profile2.save()
    
    print(f"   ✓ Created: test2@gmail.com")
    print(f"      Name: {user2.first_name} {user2.last_name}")
    print(f"      Role: Regular user (will get certifications from generate_test_certifications.py)")
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    print(f"\n✅ Created 2 demo users:")
    print(f"   1. test1@gmail.com - No certifications (for use cases 1 & 4)")
    print(f"   2. test2@gmail.com - Will get certifications (for use cases 2 & 3)")
    
    print(f"\n📝 Next steps:")
    print(f"   1. Run: python manage.py shell < testing/generate_trainings.py")
    print(f"   2. Run: python manage.py shell < testing/generate_test_certifications.py")
    print(f"      (This will add Level 1 certifications to test2@gmail.com)")
    
    print(f"\n🔑 Login credentials:")
    print(f"   Email: test1@gmail.com or test2@gmail.com")
    print(f"   Password: testpass123")
    
    print("\n" + "=" * 60)
    print("✅ Done! Demo users are ready.")
    print("=" * 60)
    print()


if __name__ == '__main__':
    generate_demo_users()
else:
    # Running in Django shell
    generate_demo_users()

