"""
Generate Shift Requirements for The Hatchery
=============================================
Run with: python manage.py shell < testing/generate_test_requirements.py

ACTUAL HATCHERY SCHEDULE:

TRAININGS:
- Monday-Thursday: 9am-10pm
- Friday: 9am-7pm  
- Saturday: 12pm-5pm (trainings only, no open hours)
- Sunday: 12pm-7pm

OPEN HOURS (hosts + floaters needed):
- Monday-Thursday: 12pm-10pm
- Friday: 12pm-7pm
- Saturday: CLOSED (no open hours)
- Sunday: 12pm-7pm

SPACES (4 total, 2 are grouped):
- 3 hosting spots needed per hour (2 groups + 1 standalone)
- 1 floater per hour minimum
"""

from datetime import time
from scheduling.models import (
    Semester, DailyOperatingHours, ShiftRequirement, LocationGroup
)
from locations.models import Location

DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


def generate_requirements():
    print("\n" + "=" * 60)
    print("GENERATING SHIFT REQUIREMENTS - THE HATCHERY")
    print("=" * 60)
    
    # Get active semester
    semester = Semester.objects.filter(is_active=True).first()
    if not semester:
        print("❌ No active semester found!")
        return
    
    print(f"\nSemester: {semester.name}")
    
    # Clear existing
    print(f"\n🗑️  Clearing existing requirements...")
    DailyOperatingHours.objects.filter(semester=semester).delete()
    ShiftRequirement.objects.filter(semester=semester).delete()
    print("   Done")
    
    # =========================================================================
    # STEP 1: Create Operating Hours
    # =========================================================================
    print(f"\n📅 Creating Operating Hours...")
    
    # Define operating hours for each day
    # open_hours = when hosts/floaters are needed
    # training = when trainings can be booked
    OPERATING_HOURS = {
        0: {  # Monday
            'is_closed': False,
            'open_hours_start': time(12, 0),   # 12pm
            'open_hours_end': time(22, 0),     # 10pm
            'training_start': time(9, 0),      # 9am
            'training_end': time(22, 0),       # 10pm
            'training_disabled': False,
        },
        1: {  # Tuesday
            'is_closed': False,
            'open_hours_start': time(12, 0),
            'open_hours_end': time(22, 0),
            'training_start': time(9, 0),
            'training_end': time(22, 0),
            'training_disabled': False,
        },
        2: {  # Wednesday
            'is_closed': False,
            'open_hours_start': time(12, 0),
            'open_hours_end': time(22, 0),
            'training_start': time(9, 0),
            'training_end': time(22, 0),
            'training_disabled': False,
        },
        3: {  # Thursday
            'is_closed': False,
            'open_hours_start': time(12, 0),
            'open_hours_end': time(22, 0),
            'training_start': time(9, 0),
            'training_end': time(22, 0),
            'training_disabled': False,
        },
        4: {  # Friday
            'is_closed': False,
            'open_hours_start': time(12, 0),   # 12pm
            'open_hours_end': time(19, 0),     # 7pm
            'training_start': time(9, 0),      # 9am
            'training_end': time(19, 0),       # 7pm
            'training_disabled': False,
        },
        5: {  # Saturday - trainings only, NO open hours
            'is_closed': False,
            'open_hours_start': time(12, 0),   # For reference only
            'open_hours_end': time(17, 0),     # 5pm
            'training_start': time(12, 0),     # 12pm
            'training_end': time(17, 0),       # 5pm
            'training_disabled': False,
            'no_hosting': True,  # Flag: no hosts/floaters needed
        },
        6: {  # Sunday
            'is_closed': False,
            'open_hours_start': time(12, 0),   # 12pm
            'open_hours_end': time(19, 0),     # 7pm
            'training_start': time(12, 0),     # 12pm
            'training_end': time(19, 0),       # 7pm
            'training_disabled': False,
        },
    }
    
    for day, config in OPERATING_HOURS.items():
        if config.get('is_closed'):
            DailyOperatingHours.objects.create(
                semester=semester,
                day_of_week=day,
                is_closed=True
            )
            print(f"   {DAY_NAMES[day]}: CLOSED")
        else:
            DailyOperatingHours.objects.create(
                semester=semester,
                day_of_week=day,
                is_closed=False,
                open_hours_start=config['open_hours_start'],
                open_hours_end=config['open_hours_end'],
                training_start=config.get('training_start'),
                training_end=config.get('training_end'),
                training_disabled=config.get('training_disabled', False)
            )
            
            if config.get('no_hosting'):
                print(f"   {DAY_NAMES[day]}: {config['open_hours_start'].strftime('%H:%M')} - {config['open_hours_end'].strftime('%H:%M')} (TRAININGS ONLY)")
            else:
                print(f"   {DAY_NAMES[day]}: {config['open_hours_start'].strftime('%H:%M')} - {config['open_hours_end'].strftime('%H:%M')}")
    
    # =========================================================================
    # STEP 2: Get Locations and Location Groups from Database
    # =========================================================================
    print(f"\n📍 Loading Locations from database...")
    
    # Get all existing locations
    all_locations = list(Location.objects.all())
    print(f"   Found {len(all_locations)} locations")
    for loc in all_locations:
        print(f"      - {loc.name}")
    
    # Get location groups (grouped locations only need 1 host for the group)
    location_groups = list(LocationGroup.objects.prefetch_related('locations').all())
    print(f"   Found {len(location_groups)} location groups")
    for group in location_groups:
        group_locs = list(group.locations.all())
        print(f"      - {group.name}: {[l.name for l in group_locs]}")
    
    # Determine hosting spots:
    # - Location groups count as 1 spot (covers multiple locations)
    # - Standalone locations (not in any group) each count as 1 spot
    grouped_location_ids = set()
    for group in location_groups:
        for loc in group.locations.all():
            grouped_location_ids.add(loc.id)
    
    standalone_locations = [loc for loc in all_locations if loc.id not in grouped_location_ids]
    
    # Total spots needing hosts = location_groups + standalone_locations
    num_host_spots = len(location_groups) + len(standalone_locations)
    print(f"\n   Hosting spots needed per hour: {num_host_spots}")
    print(f"      - {len(location_groups)} location groups")
    print(f"      - {len(standalone_locations)} standalone locations")
    
    # =========================================================================
    # STEP 3: Create Shift Requirements (hourly slots)
    # =========================================================================
    print(f"\n📋 Creating Shift Requirements...")
    print(f"   Creating HOURLY slots (1 host per spot + 1 floater per hour)")
    
    requirements_created = 0
    
    for day in range(7):
        config = OPERATING_HOURS.get(day, {})
        
        if config.get('is_closed'):
            continue
        
        open_start = config['open_hours_start']
        open_end = config['open_hours_end']
        skip_hosting = config.get('no_hosting', False)
        
        # Generate hourly slots
        current_hour = open_start.hour
        end_hour = open_end.hour
        
        while current_hour < end_hour:
            slot_start = time(current_hour, 0)
            slot_end = time(current_hour + 1, 0)
            
            if not skip_hosting:
                # Create requirement for each LOCATION GROUP (1 host per group per hour)
                for group in location_groups:
                    ShiftRequirement.objects.create(
                        semester=semester,
                        day_of_week=day,
                        time_start=slot_start,
                        time_end=slot_end,
                        location=None,
                        location_group=group,
                        hosts_required=1,
                        floaters_required=0
                    )
                    requirements_created += 1
                
                # Create requirement for each STANDALONE LOCATION (1 host each per hour)
                for location in standalone_locations:
                    ShiftRequirement.objects.create(
                        semester=semester,
                        day_of_week=day,
                        time_start=slot_start,
                        time_end=slot_end,
                        location=location,
                        location_group=None,
                        hosts_required=1,
                        floaters_required=0
                    )
                    requirements_created += 1
                
                # Create floater requirement (1 floater per hour)
                ShiftRequirement.objects.create(
                    semester=semester,
                    day_of_week=day,
                    time_start=slot_start,
                    time_end=slot_end,
                    location=None,
                    location_group=None,
                    hosts_required=0,
                    floaters_required=1
                )
                requirements_created += 1
            
            current_hour += 1
    
    print(f"   Created {requirements_created} shift requirements")
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    print(f"\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    print(f"\nOperating Hours: {DailyOperatingHours.objects.filter(semester=semester).count()} days configured")
    print(f"Locations: {len(all_locations)} ({len(location_groups)} groups, {len(standalone_locations)} standalone)")
    print(f"Hosting Spots per Hour: {num_host_spots}")
    print(f"Shift Requirements: {requirements_created}")
    
    # Calculate total hours needed per week
    total_host_hours = 0
    total_floater_hours = 0
    
    for req in ShiftRequirement.objects.filter(semester=semester):
        duration = (req.time_end.hour - req.time_start.hour) + \
                   (req.time_end.minute - req.time_start.minute) / 60
        
        total_host_hours += req.hosts_required * duration
        total_floater_hours += req.floaters_required * duration
    
    print(f"\nWeekly coverage needed:")
    print(f"   Host hours: {total_host_hours:.0f}")
    print(f"   Floater hours: {total_floater_hours:.0f}")
    print(f"   Total required: {total_host_hours + total_floater_hours:.0f} hours")
    
    # Show breakdown by day
    print(f"\nBy day:")
    for day in range(7):
        day_name = DAY_NAMES[day]
        day_reqs = ShiftRequirement.objects.filter(semester=semester, day_of_week=day)
        config = OPERATING_HOURS.get(day, {})
        
        if config.get('is_closed'):
            print(f"   {day_name}: CLOSED")
        elif config.get('no_hosting'):
            t_start = config['training_start'].strftime('%H:%M')
            t_end = config['training_end'].strftime('%H:%M')
            print(f"   {day_name}: TRAININGS ONLY ({t_start}-{t_end}) - no hosting requirements")
        elif not day_reqs.exists():
            print(f"   {day_name}: No requirements")
        else:
            host_hours = sum(r.hosts_required * 1 for r in day_reqs)  # 1 hour per slot
            floater_hours = sum(r.floaters_required * 1 for r in day_reqs)
            
            # Get time range
            times = [(r.time_start, r.time_end) for r in day_reqs]
            earliest = min(t[0] for t in times)
            latest = max(t[1] for t in times)
            
            # Also show training times if different
            t_start = config.get('training_start')
            t_end = config.get('training_end')
            
            open_str = f"Open: {earliest.strftime('%H:%M')}-{latest.strftime('%H:%M')}"
            if t_start and t_end and (t_start != earliest or t_end != latest):
                train_str = f", Training: {t_start.strftime('%H:%M')}-{t_end.strftime('%H:%M')}"
            else:
                train_str = ""
            
            print(f"   {day_name}: {open_str}{train_str} | {host_hours} host-hrs, {floater_hours} floater-hrs")
    
    print(f"\n✅ Done!")


# Run it
generate_requirements()