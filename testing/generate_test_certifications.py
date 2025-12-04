"""
Generate Test User Certifications for Demo
==========================================

Creates UserTrainingRecord objects (certifications) for test users:
- test1@gmail.com: 0 certifications (user with no training)
- test2@gmail.com: All Level 1 trainings completed (user with some training)

This supports the 4 demo use cases:
1. User with no training selecting a training
2. User with some training selecting a training
3. User with training selecting a machine (they have the required training)
4. User without training selecting a machine (they don't have the required training)

Run with:
    python manage.py shell < testing/generate_test_certifications.py
"""

from django.utils import timezone
from datetime import date, timedelta
from machines.models import Training, UserTrainingRecord
from accounts.models import User, Certification


def generate_certifications():
    """Generate certifications for test users."""
    
    print("=" * 60)
    print("GENERATING TEST USER CERTIFICATIONS")
    print("=" * 60)
    
    # Step 1: Find test users
    print("\n📋 Finding test users...")
    try:
        test_user_1 = User.objects.get(email='test1@gmail.com')
        print(f"   ✓ Found: test1@gmail.com (ID: {test_user_1.id})")
    except User.DoesNotExist:
        print("   ❌ ERROR: test1@gmail.com not found!")
        print("   Please run generate_test_users.py first.")
        return
    
    try:
        test_user_2 = User.objects.get(email='test2@gmail.com')
        print(f"   ✓ Found: test2@gmail.com (ID: {test_user_2.id})")
    except User.DoesNotExist:
        print("   ❌ ERROR: test2@gmail.com not found!")
        print("   Please run generate_test_users.py first.")
        return
    
    # Step 2: Clear existing certifications for both users
    print("\n🗑️  Clearing existing certifications...")
    deleted_1 = UserTrainingRecord.objects.filter(user=test_user_1).delete()
    deleted_2 = UserTrainingRecord.objects.filter(user=test_user_2).delete()
    cert_deleted_1 = Certification.objects.filter(user=test_user_1).delete()
    cert_deleted_2 = Certification.objects.filter(user=test_user_2).delete()
    print(f"   Deleted {deleted_1[0]} training records for test1@gmail.com")
    print(f"   Deleted {deleted_2[0]} training records for test2@gmail.com")
    print(f"   Deleted {cert_deleted_1[0]} certifications for test1@gmail.com")
    print(f"   Deleted {cert_deleted_2[0]} certifications for test2@gmail.com")
    
    # Step 3: Get all Level 1 active trainings
    print("\n📚 Finding Level 1 trainings...")
    level_1_trainings = Training.objects.filter(
        level=1,
        status='active'
    ).order_by('category', 'name')
    
    training_count = level_1_trainings.count()
    print(f"   Found {training_count} Level 1 active trainings")
    
    if training_count == 0:
        print("   ⚠️  WARNING: No Level 1 trainings found!")
        print("   Please run generate_trainings.py first.")
        return
    
    # Step 4: Create certifications for test2@gmail.com
    print("\n🎓 Creating certifications for test2@gmail.com...")
    created_count = 0
    created_trainings = []
    completed_at = timezone.now()
    issued_date = date.today()
    
    for training in level_1_trainings:
        # Create UserTrainingRecord (for machine reservation checks)
        record, created = UserTrainingRecord.objects.get_or_create(
            user=test_user_2,
            training=training,
            defaults={
                'status': 'completed',
                'completed_at': completed_at,
                'trainer': None,  # No specific trainer assigned
                'notes': 'Generated for demo purposes'
            }
        )
        
        # Create Certification (for dashboard display)
        cert, cert_created = Certification.objects.get_or_create(
            user=test_user_2,
            name=training.name,
            defaults={
                'issued_at': issued_date,
                'expires_at': None  # No expiration for demo
            }
        )
        
        if created:
            created_count += 1
            created_trainings.append(training.name)
            print(f"   ✓ {training.name} ({training.category})")
        else:
            print(f"   - {training.name} (already exists)")
    
    # Step 5: Verify test1@gmail.com has 0 certifications
    test1_training_count = UserTrainingRecord.objects.filter(user=test_user_1).count()
    test1_cert_count = Certification.objects.filter(user=test_user_1).count()
    
    # Step 6: Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    print(f"\n✅ test1@gmail.com:")
    print(f"   Training Records: {test1_training_count}")
    print(f"   Certifications: {test1_cert_count}")
    print(f"   (User with no training - for demo use case 1 & 4)")
    
    test2_cert_count = Certification.objects.filter(user=test_user_2).count()
    print(f"\n✅ test2@gmail.com:")
    print(f"   Training Records: {created_count}")
    print(f"   Certifications: {test2_cert_count}")
    print(f"   (User with some training - for demo use case 2 & 3)")
    
    if created_trainings:
        print(f"\n📋 Certifications created:")
        for training_name in created_trainings:
            print(f"   • {training_name}")
    
    # Group by category for better overview
    print(f"\n📊 Certifications by category:")
    category_counts = {}
    for training in level_1_trainings:
        category = training.category
        if category not in category_counts:
            category_counts[category] = 0
        if training.name in created_trainings:
            category_counts[category] += 1
    
    for category, count in sorted(category_counts.items()):
        print(f"   {category}: {count} training(s)")
    
    print("\n" + "=" * 60)
    print("✅ Done! Demo users are ready for testing.")
    print("=" * 60)
    print("\nDemo Use Cases:")
    print("  1. test1@gmail.com → Browse/select trainings (no certifications)")
    print("  2. test2@gmail.com → Browse/select trainings (has Level 1 certs)")
    print("  3. test2@gmail.com → Reserve machines (has required training)")
    print("  4. test1@gmail.com → Try to reserve machines (no training)")
    print()


if __name__ == '__main__':
    generate_certifications()
else:
    # Running in Django shell
    generate_certifications()

