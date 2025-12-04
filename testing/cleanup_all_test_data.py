"""
Cleanup All Test Data
=====================

Deletes all test data to start fresh:
- Test users (test1@gmail.com, test2@gmail.com, and all test*@gmail.com)
- Training sessions
- Training bookings
- User training records (certifications)
- Machine reservations
- Test machines (optional)

Usage:
    python manage.py shell < testing/cleanup_all_test_data.py
"""

from django.contrib.auth import get_user_model
from machines.models import Training, UserTrainingRecord, Machine
from reservations.models import TrainingSession, TrainingBooking, MachineReservation
from accounts.models import Certification
from locations.models import Location
from scheduling.models import TeamMemberProfile

User = get_user_model()


def cleanup_all_test_data():
    """Delete all test data."""
    
    print("=" * 60)
    print("CLEANING UP ALL TEST DATA")
    print("=" * 60)
    
    # 1. Delete test users and related data
    print("\n🗑️  Deleting test users...")
    test_users = User.objects.filter(email__startswith='test', email__endswith='@gmail.com')
    user_count = test_users.count()
    
    # Delete related data first
    print("   Deleting related data...")
    
    # Training bookings
    bookings_deleted = TrainingBooking.objects.filter(user__in=test_users).delete()
    print(f"   Deleted {bookings_deleted[0]} training bookings")
    
    # Machine reservations
    reservations_deleted = MachineReservation.objects.filter(user__in=test_users).delete()
    print(f"   Deleted {reservations_deleted[0]} machine reservations")
    
    # User training records
    records_deleted = UserTrainingRecord.objects.filter(user__in=test_users).delete()
    print(f"   Deleted {records_deleted[0]} user training records")
    
    # Certifications
    certs_deleted = Certification.objects.filter(user__in=test_users).delete()
    print(f"   Deleted {certs_deleted[0]} certifications")
    
    # Team member profiles
    profiles_deleted = TeamMemberProfile.objects.filter(user__in=test_users).delete()
    print(f"   Deleted {profiles_deleted[0]} team member profiles")
    
    # Delete users
    users_deleted = test_users.delete()
    print(f"   Deleted {users_deleted[0]} test users")
    
    # 2. Delete training sessions (optional - comment out if you want to keep them)
    print("\n🗑️  Deleting training sessions...")
    sessions_deleted = TrainingSession.objects.all().delete()
    print(f"   Deleted {sessions_deleted[0]} training sessions")
    
    # 3. Clear machine_type_names from trainings (optional)
    print("\n🗑️  Clearing machine links from trainings...")
    trainings = Training.objects.all()
    cleared_count = 0
    for training in trainings:
        if training.machine_type_names:
            training.machine_type_names = []
            training.save()
            cleared_count += 1
    print(f"   Cleared machine links from {cleared_count} trainings")
    
    # 4. Optional: Delete test machines (uncomment if you want to delete machines too)
    # print("\n🗑️  Deleting test machines...")
    # machines_deleted = Machine.objects.all().delete()
    # print(f"   Deleted {machines_deleted[0]} machines")
    
    # 5. Optional: Delete location (uncomment if you want to delete location too)
    # print("\n🗑️  Deleting demo location...")
    # location_deleted = Location.objects.all().delete()
    # print(f"   Deleted {location_deleted[0]} locations")
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"\n✅ Cleaned up:")
    print(f"   - {users_deleted[0]} test users")
    print(f"   - {bookings_deleted[0]} training bookings")
    print(f"   - {reservations_deleted[0]} machine reservations")
    print(f"   - {records_deleted[0]} user training records")
    print(f"   - {certs_deleted[0]} certifications")
    print(f"   - {sessions_deleted[0]} training sessions")
    print(f"   - Cleared machine links from {cleared_count} trainings")
    
    print("\n" + "=" * 60)
    print("✅ Cleanup complete! Ready to run setup from scratch.")
    print("=" * 60)
    print("\nNext steps:")
    print("   1. python manage.py shell < testing/generate_demo_location.py")
    print("   2. python manage.py shell < testing/generate_test_machines.py")
    print("   3. python manage.py shell < testing/generate_demo_users.py")
    print("   4. python manage.py shell < testing/generate_test_requirements.py")
    print("   5. python manage.py shell < testing/generate_test_unavailabilities.py")
    print("   6. python manage.py shell < testing/generate_trainings.py")
    print("   7. python manage.py shell < testing/generate_test_certifications.py")
    print("   8. python manage.py shell < testing/generate_demo_training_sessions.py")
    print("   9. python manage.py shell < testing/link_machines_to_trainings.py")
    print()


if __name__ == '__main__':
    cleanup_all_test_data()
else:
    # Running in Django shell
    cleanup_all_test_data()

