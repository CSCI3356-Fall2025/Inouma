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
    
    # Get all available trainers (or create a dummy one)
    trainers = list(User.objects.filter(is_trainer=True))
    if not trainers:
        # Use test2@gmail.com as trainer if no trainers exist
        trainer = User.objects.filter(email='test2@gmail.com').first()
        if trainer:
            trainer.is_trainer = True
            trainer.save()
            trainers = [trainer]
            print(f"\n👤 Using test2@gmail.com as trainer")
        else:
            print("\n❌ ERROR: No trainer found!")
            print("   Please run generate_demo_users.py first.")
            return
    else:
        print(f"\n👤 Found {len(trainers)} trainer(s):")
        from scheduling.models import TeamMemberProfile
        for t in trainers:
            team = getattr(t, 'team_assignment', '') or ''
            if not team:
                try:
                    team_profile = TeamMemberProfile.objects.get(user=t)
                    team = getattr(team_profile, 'team', '') or ''
                except TeamMemberProfile.DoesNotExist:
                    team = ''
            print(f"   - {t.get_full_name() or t.email} ({t.email}) - Team: {team or 'Unassigned'}")
    
    # Build trainer lookup by category
    # Map category name to list of trainers for that category
    trainers_by_category = {}
    from scheduling.models import TeamMemberProfile
    
    for trainer in trainers:
        # Get team assignment from User.team_assignment or TeamMemberProfile.team
        team = getattr(trainer, 'team_assignment', '') or ''
        
        # Try to get from TeamMemberProfile if not in User model
        if not team:
            try:
                team_profile = TeamMemberProfile.objects.get(user=trainer)
                team = getattr(team_profile, 'team', '') or ''
            except TeamMemberProfile.DoesNotExist:
                team = ''
        
        # Normalize category names (handle variations and case)
        if team:
            # Normalize to match Training.category format
            team = team.strip()
            # Map common variations (case-insensitive)
            category_map = {
                'laser': 'Laser',
                '3d printing': '3D Printing',
                'woodworking': 'Woodworking',
                'textile': 'Textile',
                'metalworking': 'Metalworking',
                'vinyl': 'Vinyl',
                'electronics': 'Electronics',
            }
            # Try exact match first, then case-insensitive lookup
            normalized_team = category_map.get(team.lower(), team)
            # If still not matching, try direct match with Training categories
            if normalized_team not in ['Laser', '3D Printing', 'Woodworking', 'Textile', 'Metalworking', 'Vinyl', 'Electronics']:
                # Try to find matching category (case-insensitive)
                for cat in ['Laser', '3D Printing', 'Woodworking', 'Textile', 'Metalworking', 'Vinyl', 'Electronics']:
                    if team.lower() == cat.lower():
                        normalized_team = cat
                        break
            
            if normalized_team not in trainers_by_category:
                trainers_by_category[normalized_team] = []
            trainers_by_category[normalized_team].append(trainer)
    
    # Also create a fallback list of all trainers for categories without specific trainers
    all_trainers_list = trainers
    print(f"\n📋 Trainer distribution by category:")
    for category, cat_trainers in trainers_by_category.items():
        print(f"   {category}: {len(cat_trainers)} trainer(s)")
    if not trainers_by_category:
        print(f"   No category-specific trainers found, will use all trainers as fallback")
    
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
    
    # Track trainer indices per category for round-robin distribution
    trainer_indices_by_category = {cat: 0 for cat in trainers_by_category.keys()}
    # Also track for fallback (all trainers)
    fallback_trainer_index = 0
    
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
                
                # Find trainers for this training's category
                training_category = training.category
                
                # Debug: Print category matching
                if sessions_created == 0:
                    print(f"\n🔍 Category matching debug:")
                    print(f"   Training category: '{training_category}'")
                    print(f"   Available trainer categories: {list(trainers_by_category.keys())}")
                
                category_trainers = trainers_by_category.get(training_category, [])
                
                # Assign trainer using round-robin from category-specific trainers
                if category_trainers:
                    # Use round-robin within the category
                    trainer_index = trainer_indices_by_category.get(training_category, 0)
                    assigned_trainer = category_trainers[trainer_index % len(category_trainers)]
                    trainer_indices_by_category[training_category] = (trainer_index + 1) % len(category_trainers)
                elif all_trainers_list:
                    # If no trainers for this category, use all trainers as fallback with round-robin
                    assigned_trainer = all_trainers_list[fallback_trainer_index % len(all_trainers_list)]
                    fallback_trainer_index += 1
                    if sessions_created < 3:  # Print warning for first few sessions
                        trainer_name = assigned_trainer.get_full_name() or assigned_trainer.email
                        trainer_team = getattr(assigned_trainer, 'team_assignment', '') or ''
                        print(f"   ⚠️  No trainers found for '{training_category}', using {trainer_name} (team: {trainer_team or 'Unassigned'})")
                else:
                    # Last resort: no trainers available
                    print(f"   ❌ No trainers available for {training.name}, skipping...")
                    continue
                
                # Check if session already exists
                existing = TrainingSession.objects.filter(
                    trainer=assigned_trainer,
                    training=training,
                    date=session_date,
                    start_time=start_time
                ).exists()
                
                if not existing:
                    session = TrainingSession.objects.create(
                        trainer=assigned_trainer,
                        training=training,
                        date=session_date,
                        start_time=start_time,
                        end_time=end_time,
                        location=location,
                        max_participants=training.max_participants or 4,
                        status='available'
                    )
                    sessions_created += 1
                    trainer_name = assigned_trainer.get_full_name() or assigned_trainer.email
                    print(f"   ✓ {training.name} - {session_date} {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')} (Trainer: {trainer_name})")
    
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

