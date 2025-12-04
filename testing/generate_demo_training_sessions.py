"""
Generate Demo Training Sessions
================================

Creates TrainingSession objects for the next 2 weeks so users can book trainings.
This is needed for the demo - training sessions are what users actually sign up for.

PRIORITY: If Shift objects exist (from auto-scheduler), generates TrainingSessions from them.
FALLBACK: If no Shifts exist, creates TrainingSessions directly (for demo purposes).

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
    
    # Check if we should generate from Shifts (preferred) or create directly (fallback)
    from scheduling.models import Shift, Semester
    
    today = date.today()
    end_date = today + timedelta(days=14)
    
    # Check for training shifts in the next 2 weeks
    training_shifts = Shift.objects.filter(
        shift_type='training',
        date__gte=today,
        date__lte=end_date,
        status='scheduled'
    )
    
    if training_shifts.exists():
        print("\n📋 Found existing training shifts - generating sessions from shifts...")
        print(f"   Found {training_shifts.count()} training shifts")
        return generate_from_shifts(training_shifts, today, end_date)
    else:
        print("\n📋 No training shifts found - creating sessions directly (demo mode)...")
        return generate_directly(today, end_date)


def generate_from_shifts(shifts, start_date, end_date):
    """Generate TrainingSession objects from existing Shift objects."""
    from machines.models import Training
    
    print("\n🔄 Generating TrainingSessions from Shifts...")
    sessions_created = 0
    
    # Get all active trainings grouped by category
    trainings_by_category = {}
    for training in Training.objects.filter(status='active'):
        cat = (training.category or 'general').lower().strip()
        if cat not in trainings_by_category:
            trainings_by_category[cat] = []
        trainings_by_category[cat].append(training)
    
    for shift in shifts.select_related('user', 'location'):
        try:
            # Determine category from shift
            category = (shift.team_category or 'general').strip()
            category_lower = category.lower()
            
            # Find matching trainings for this category
            matching_trainings = trainings_by_category.get(category_lower, [])
            
            # Try fuzzy match if exact match fails
            if not matching_trainings:
                for cat_key, trainings in trainings_by_category.items():
                    if cat_key in category_lower or category_lower in cat_key:
                        matching_trainings = trainings
                        break
            
            if not matching_trainings:
                print(f"   ⚠️  Shift {shift.id}: No trainings found for category '{category}'")
                continue
            
            # Create only ONE session per shift - use the primary training (Level 1, or first one)
            # This prevents multiple sessions at the same time slot
            primary_training = None
            for training in matching_trainings:
                if training.level == 1:
                    primary_training = training
                    break
            
            # If no Level 1, use the first training
            if not primary_training and matching_trainings:
                primary_training = matching_trainings[0]
            
            if not primary_training:
                print(f"   ⚠️  Shift {shift.id}: No training found to create session")
                continue
            
            # Check if session already exists for this shift
            existing = TrainingSession.objects.filter(
                source_shift=shift,
                training=primary_training
            ).exists()
            
            if existing:
                continue
            
            # Determine max participants
            max_participants = getattr(primary_training, 'max_participants', None) or 4
            
            # Create the session
            session = TrainingSession.objects.create(
                training=primary_training,
                trainer=shift.user,
                date=shift.date,
                start_time=shift.start_time,
                end_time=shift.end_time,
                location=shift.location,
                max_participants=max_participants,
                source_shift=shift,
                status='available',
                notes=f'Auto-generated from shift #{shift.id}'
            )
            sessions_created += 1
            trainer_name = shift.user.get_full_name() or shift.user.email
            print(f"   ✓ Shift {shift.id} ({shift.date}): {primary_training.name} - Trainer: {trainer_name}")
                
        except Exception as e:
            import traceback
            print(f"   ⚠️  Error processing shift {shift.id}: {e}")
            traceback.print_exc()
    
    print(f"\n✅ Created {sessions_created} training sessions from shifts")
    return sessions_created


def generate_directly(start_date, end_date):
    """Generate TrainingSession objects directly (fallback for demo)."""
    
    print("=" * 60)
    print("GENERATING DEMO TRAINING SESSIONS (Direct Mode)")
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
    
    # Group trainings by category and create ONE session per category per time slot
    # This prevents multiple sessions for the same trainer at the same time
    trainings_by_category_dict = {}
    for training in trainings:
        cat = training.category or 'general'
        if cat not in trainings_by_category_dict:
            trainings_by_category_dict[cat] = []
        trainings_by_category_dict[cat].append(training)
    
    # Create sessions: ONE per category per time slot
    # Use Level 1 training for each category (or first available)
    time_slots = [
        (time(9, 0), time(10, 0)),   # 9:00 AM - 10:00 AM
        (time(10, 0), time(11, 0)),  # 10:00 AM - 11:00 AM
        (time(11, 0), time(12, 0)),  # 11:00 AM - 12:00 PM
        (time(14, 0), time(15, 0)),  # 2:00 PM - 3:00 PM
    ]
    
    # Track which time slots have been used per trainer per date
    trainer_time_slots_used = {}  # key: (trainer_id, date, time_str) -> True
    
    for category, category_trainings in trainings_by_category_dict.items():
        # Get primary training for this category (Level 1, or first)
        primary_training = None
        for t in category_trainings:
            if t.level == 1:
                primary_training = t
                break
        if not primary_training:
            primary_training = category_trainings[0]
        
        # Find trainers for this category
        category_trainers = trainers_by_category.get(category, [])
        if not category_trainers:
            category_trainers = all_trainers_list
        
        if not category_trainers:
            print(f"   ⚠️  No trainers available for category '{category}', skipping...")
            continue
        
        # Create 2-3 sessions per category, spread across 2 weeks
        for week_offset in range(2):
            for day_offset in [0, 2, 4]:  # Monday, Wednesday, Friday
                session_date = today + timedelta(days=(week_offset * 7) + day_offset)
                
                # Skip if date is more than 14 days away
                if (session_date - today).days > 14:
                    continue
                
                # Pick a time slot that hasn't been used by this trainer on this date
                assigned_trainer = None
                assigned_time_slot = None
                
                for trainer in category_trainers:
                    trainer_id = trainer.id
                    for time_slot in time_slots:
                        start_time, end_time = time_slot
                        time_key = (trainer_id, session_date, start_time.strftime('%H:%M'))
                        
                        if time_key not in trainer_time_slots_used:
                            assigned_trainer = trainer
                            assigned_time_slot = time_slot
                            trainer_time_slots_used[time_key] = True
                            break
                    
                    if assigned_trainer:
                        break
                
                if not assigned_trainer or not assigned_time_slot:
                    # All time slots for this date are taken, skip
                    continue
                
                start_time, end_time = assigned_time_slot
                
                # Check if session already exists
                existing = TrainingSession.objects.filter(
                    trainer=assigned_trainer,
                    training=primary_training,
                    date=session_date,
                    start_time=start_time
                ).exists()
                
                if not existing:
                    session = TrainingSession.objects.create(
                        trainer=assigned_trainer,
                        training=primary_training,
                        date=session_date,
                        start_time=start_time,
                        end_time=end_time,
                        location=location,
                        max_participants=primary_training.max_participants or 4,
                        status='available'
                    )
                    sessions_created += 1
                    trainer_name = assigned_trainer.get_full_name() or assigned_trainer.email
                    print(f"   ✓ {primary_training.name} ({category}) - {session_date} {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')} (Trainer: {trainer_name})")
    
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

