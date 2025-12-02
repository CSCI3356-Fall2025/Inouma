"""
Run Scheduler with Detailed Output
==================================
Run with: python manage.py shell < testing/run_scheduler.py
"""

from scheduling.weekly_scheduler import WeeklyScheduler
from scheduling.models import Semester, ShiftRequirement, Shift
from collections import defaultdict

DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

def run_and_analyze():
    print("\n" + "=" * 70)
    print("RUNNING SCHEDULER WITH ANALYSIS")
    print("=" * 70)
    
    semester = Semester.objects.filter(is_active=True).first()
    if not semester:
        print("❌ No active semester!")
        return
    
    print(f"\n📅 Semester: {semester.name}")
    print(f"   Date range: {semester.start_date} to {semester.end_date}")
    
    # Show requirements BEFORE running
    print("\n" + "-" * 50)
    print("REQUIREMENTS (what we need to fill)")
    print("-" * 50)
    
    for day in range(7):
        reqs = ShiftRequirement.objects.filter(
            semester=semester,
            day_of_week=day
        ).order_by('time_start')
        
        if not reqs.exists():
            print(f"   {DAY_NAMES[day]}: No requirements")
            continue
        
        slots = defaultdict(lambda: {'hosts': 0, 'floaters': 0})
        for r in reqs:
            key = f"{r.time_start.strftime('%H:%M')}-{r.time_end.strftime('%H:%M')}"
            slots[key]['hosts'] += r.hosts_required
            slots[key]['floaters'] += r.floaters_required
        
        print(f"   {DAY_NAMES[day]}:")
        for slot, counts in sorted(slots.items()):
            print(f"      {slot}: {counts['hosts']}H + {counts['floaters']}F")
    
    # Run the scheduler
    print("\n" + "-" * 50)
    print("RUNNING SCHEDULER")
    print("-" * 50)
    
    scheduler = WeeklyScheduler(semester)
    result = scheduler.run()
    
    # Show results
    print("\n" + "-" * 50)
    print("RESULTS")
    print("-" * 50)
    print(f"   Success: {result['success']}")
    print(f"   Shifts created: {result['shifts_created']}")
    print(f"   Conflicts: {len(result['conflicts'])}")
    
    if result['conflicts']:
        print("\n   ⚠️ CONFLICTS (unfilled slots):")
        # Group by day
        by_day = defaultdict(list)
        for c in result['conflicts']:
            by_day[c['day']].append(c)
        
        for day in DAY_NAMES:
            if day in by_day:
                print(f"      {day}:")
                for c in by_day[day]:
                    print(f"         {c['time']} @ {c['location']} ({c['type']})")
    
    # Analyze what was actually created
    print("\n" + "-" * 50)
    print("SHIFTS CREATED (model week - first occurrence of each day)")
    print("-" * 50)
    
    shifts = Shift.objects.filter(semester=semester).order_by('date', 'start_time')
    
    # Get ONLY the first occurrence of each weekday
    first_week = {}
    seen_dates = set()
    for s in shifts:
        day_name = DAY_NAMES[s.date.weekday()]
        date_str = s.date.isoformat()
        
        # Only take shifts from the first occurrence of this weekday
        if day_name not in first_week:
            first_week[day_name] = {'date': s.date, 'shifts': []}
        
        if s.date == first_week[day_name]['date']:
            first_week[day_name]['shifts'].append(s)
    
    for day in DAY_NAMES:
        day_data = first_week.get(day, {})
        day_shifts = day_data.get('shifts', [])
        day_date = day_data.get('date', 'N/A')
        
        if not day_shifts:
            print(f"   {day}: NO SHIFTS!")
            continue
        
        # Group by time
        by_time = defaultdict(list)
        for s in day_shifts:
            key = f"{s.start_time.strftime('%H:%M')}-{s.end_time.strftime('%H:%M')}"
            by_time[key].append(s)
        
        print(f"   {day} ({day_date}):")
        for slot, slot_shifts in sorted(by_time.items()):
            types = defaultdict(int)
            for s in slot_shifts:
                types[s.shift_type] += 1
            type_str = ", ".join(f"{c} {t}" for t, c in sorted(types.items()))
            print(f"      {slot}: {type_str}")
    
    print("\n" + "=" * 70)
    print("VERIFICATION: Checking if all requirements are met")
    print("=" * 70)
    
    # For each day, check if requirements match shifts
    all_good = True
    for day in range(7):
        day_name = DAY_NAMES[day]
        
        # Get requirements
        reqs = ShiftRequirement.objects.filter(semester=semester, day_of_week=day)
        if not reqs.exists():
            continue
        
        # Get first week's shifts for this day
        day_data = first_week.get(day_name, {})
        day_shifts = day_data.get('shifts', [])
        
        # Check each requirement
        for req in reqs:
            slot = f"{req.time_start.strftime('%H:%M')}-{req.time_end.strftime('%H:%M')}"
            
            # Count shifts matching this slot
            matching = [s for s in day_shifts 
                       if s.start_time == req.time_start and s.end_time == req.time_end]
            
            open_hours_count = len([s for s in matching if s.shift_type == 'open_hours'])
            floater_count = len([s for s in matching if s.shift_type == 'floater'])
            
            if open_hours_count < req.hosts_required or floater_count < req.floaters_required:
                all_good = False
                print(f"   ❌ {day_name} {slot}: Need {req.hosts_required}H/{req.floaters_required}F, got {open_hours_count}H/{floater_count}F")
    
    if all_good:
        print("   ✅ All requirements met!")
    
    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


# Run it
run_and_analyze()