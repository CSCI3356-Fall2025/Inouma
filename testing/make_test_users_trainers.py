"""
Make Test Users Trainers
========================

Makes test1@gmail.com and test2@gmail.com trainers so they can lead training sessions.

Requirements for training shifts:
1. User.is_trainer = True
2. TeamMemberProfile.is_trainer = True
3. TeamMemberProfile.team = valid category (already set)
4. TeamMemberProfile.is_active = True (already set)

Run with:
    python manage.py shell < testing/make_test_users_trainers.py
"""

from django.contrib.auth import get_user_model
from scheduling.models import TeamMemberProfile

User = get_user_model()


def make_test_users_trainers():
    """Make test users trainers."""
    
    print("=" * 60)
    print("MAKING TEST USERS TRAINERS")
    print("=" * 60)
    
    # Update test1@gmail.com
    print("\n👤 Making test1@gmail.com a trainer...")
    try:
        user1 = User.objects.get(email='test1@gmail.com')
        
        # Update User model
        user1.is_trainer = True
        user1.save()
        
        # Update TeamMemberProfile
        try:
            profile1 = TeamMemberProfile.objects.get(user=user1)
            profile1.is_trainer = True
            profile1.save()
            print(f"   ✓ Updated User.is_trainer = True")
            print(f"   ✓ Updated TeamMemberProfile.is_trainer = True")
            print(f"   ✓ Team: {profile1.team}")
            print(f"   ✓ Will lead training sessions for: {profile1.team}")
        except TeamMemberProfile.DoesNotExist:
            print("   ⚠️  Warning: No TeamMemberProfile found!")
            print("   Run: python manage.py shell < testing/update_test_users_for_shifts.py")
        
    except User.DoesNotExist:
        print("   ❌ ERROR: test1@gmail.com not found!")
        print("   Run: python manage.py shell < testing/generate_demo_users.py")
    
    # Update test2@gmail.com
    print("\n👤 Making test2@gmail.com a trainer...")
    try:
        user2 = User.objects.get(email='test2@gmail.com')
        
        # Update User model
        user2.is_trainer = True
        user2.save()
        
        # Update TeamMemberProfile
        try:
            profile2 = TeamMemberProfile.objects.get(user=user2)
            profile2.is_trainer = True
            profile2.save()
            print(f"   ✓ Updated User.is_trainer = True")
            print(f"   ✓ Updated TeamMemberProfile.is_trainer = True")
            print(f"   ✓ Team: {profile2.team}")
            print(f"   ✓ Will lead training sessions for: {profile2.team}")
        except TeamMemberProfile.DoesNotExist:
            print("   ⚠️  Warning: No TeamMemberProfile found!")
            print("   Run: python manage.py shell < testing/update_test_users_for_shifts.py")
        
    except User.DoesNotExist:
        print("   ❌ ERROR: test2@gmail.com not found!")
        print("   Run: python manage.py shell < testing/generate_demo_users.py")
    
    # Verify
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    
    trainers = User.objects.filter(
        email__in=['test1@gmail.com', 'test2@gmail.com'],
        is_trainer=True
    )
    
    print(f"\n✅ Found {trainers.count()} test users as trainers:")
    for user in trainers:
        try:
            profile = TeamMemberProfile.objects.get(user=user)
            print(f"   - {user.email}: {profile.team} training (is_trainer={profile.is_trainer}, is_active={profile.is_active})")
        except TeamMemberProfile.DoesNotExist:
            print(f"   - {user.email}: User.is_trainer=True (but no profile)")
    
    print("\n" + "=" * 60)
    print("✅ Done! Test users are now trainers.")
    print("=" * 60)
    print("\n📝 Next steps:")
    print("   1. Clear existing schedule (if needed)")
    print("   2. Run auto-scheduler - test users will get training shifts")
    print("   3. Training sessions will be generated from their shifts")
    print()


if __name__ == '__main__':
    make_test_users_trainers()
else:
    # Running in Django shell
    make_test_users_trainers()

