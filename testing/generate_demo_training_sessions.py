"""
Generate Demo Training Sessions
================================

Creates TrainingSession objects for the next 2 weeks so users can book trainings.
This is needed for the demo - training sessions are what users actually sign up for.

Run with:
    python manage.py shell < testing/generate_demo_training_sessions.py
"""

from django.utils import timezone
from datetime import date, timedelta, time
from machines.models import Training
from reservations.models import TrainingSession
from locations.models import Location
from accounts.models import User


def generate_demo_training_sessions():
    """Generate training sessions for the next 2 weeks."""
    
    print("=" * 60)
    print("GENERATING DEMO TRAINING SESSIONS")
    print("=" * 60)
    
    # Get location
    location = Location.objects.first()
    if not location:
        print("\n❌ ERROR: No location found!")
        print("   Please run generate_demo_location.py first.")
        return
    
    print(f"\n📍 Using location: {location.name}")
    
    # Get a trainer (or create a dummy one)
    trainer = User.objects.filter(is_trainer=True).first()
    if not trainer:
        # Use test2@gmail.com as trainer if no trainers exist
        trainer = User.objects.filter(email='test2@gmail.com').first()
        if trainer:
            trainer.is_trainer = True
            trainer.save()
            print(f"\n👤 Using test2@gmail.com as trainer")
        else:
            print("\n❌ ERROR: No trainer found!")
            print("   Please run generate_demo_users.py first.")
            return
    else:
        print(f"\n👤 Using trainer: {trainer.email}")
    
    # Get all active trainings (Level 1, 2, and 3) so users can see sessions
    # Level 1 for test1@gmail.com, Level 2+ for test2@gmail.com
    trainings = Training.objects.filter(status='active').order_by('level', 'category', 'name')
    training_count = trainings.count()
    
    if training_count == 0:
        print("\n❌ ERROR: No trainings found!")
        print("   Please run generate_trainings.py first.")
        return
    
    level_1_count = trainings.filter(level=1).count()
    level_2_count = trainings.filter(level=2).count()
    level_3_count = trainings.filter(level=3).count()
    
    print(f"\n📚 Found {training_count} active trainings:")
    print(f"   Level 1: {level_1_count}")
    print(f"   Level 2: {level_2_count}")
    print(f"   Level 3: {level_3_count}")
    
    # Clear existing demo sessions (optional - comment out to keep existing)
    print("\n🗑️  Clearing existing training sessions...")
    deleted = TrainingSession.objects.filter(
        date__gte=date.today(),
        date__lte=date.today() + timedelta(days=14)
    ).delete()
    print(f"   Deleted {deleted[0]} existing sessions")
    
    # Generate sessions for the next 2 weeks
    print("\n📅 Creating training sessions for next 2 weeks...")
    today = date.today()
    sessions_created = 0
    
    # Create sessions for all trainings (so both test1 and test2 can see some)
    # test1@gmail.com will see Level 1 sessions (they have no certs)
    # test2@gmail.com will see Level 2+ sessions (they've completed Level 1)
    for training in trainings:
        # Create 2 sessions per training
        for i in range(2):
            # Spread sessions across 2 weeks
            session_date = today + timedelta(days=(i * 7) + (hash(training.name) % 7))
            
            # Skip if date is more than 14 days away
            if (session_date - today).days > 14:
                continue
            
            # Create morning and afternoon sessions
            for time_slot in [
                (time(10, 0), time(11, 0)),  # 10:00 AM - 11:00 AM
                (time(14, 0), time(15, 0)),  # 2:00 PM - 3:00 PM
            ]:
                start_time, end_time = time_slot
                
                # Check if session already exists
                existing = TrainingSession.objects.filter(
                    trainer=trainer,
                    training=training,
                    date=session_date,
                    start_time=start_time
                ).exists()
                
                if not existing:
                    session = TrainingSession.objects.create(
                        trainer=trainer,
                        training=training,
                        date=session_date,
                        start_time=start_time,
                        end_time=end_time,
                        location=location,
                        max_participants=training.max_participants or 4,
                        status='available'
                    )
                    sessions_created += 1
                    print(f"   ✓ {training.name} - {session_date} {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"\n✅ Created {sessions_created} training sessions")
    print(f"   Available for booking in the next 2 weeks")
    
    # Count by training
    print(f"\n📊 Sessions by training:")
    for training in trainings:
        count = TrainingSession.objects.filter(
            training=training,
            date__gte=today,
            date__lte=today + timedelta(days=14)
        ).count()
        if count > 0:
            print(f"   {training.name}: {count} session(s)")
    
    print("\n" + "=" * 60)
    print("✅ Done! Users can now book training sessions.")
    print("=" * 60)
    print("\nUsers can now:")
    print("  1. Go to /reservations/training/ to browse sessions")
    print("  2. Click on a session to book it")
    print("  3. After booking and completion, they'll get certifications")
    print()


if __name__ == '__main__':
    generate_demo_training_sessions()
else:
    # Running in Django shell
    generate_demo_training_sessions()

