"""
Scheduler Diagnostic Script
============================
Run with: python manage.py shell < testing/diagnose_scheduler.py
"""

from scheduling.models import DailyOperatingHours, ShiftRequirement, Semester, TeamMemberProfile
from django.db.models import Count

DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

def run_diagnostics():
    print("\n" + "=" * 60)
    print("SCHEDULER DIAGNOSTICS")
    print("=" * 60)
    
    # Get active semester
    semester = Semester.objects.filter(is_active=True).first()
    if not semester:
        print("❌ No active semester found!")
        return
    
    print(f"\n📅 Semester: {semester.name}")
    
    # =========================================================================
    # 1. Operating Hours
    # =========================================================================
    print("\n" + "-" * 40)
    print("1. OPERATING HOURS")
    print("-" * 40)
    
    op_hours = DailyOperatingHours.objects.filter(semester=semester).order_by('day_of_week')
    
    if not op_hours.exists():
        print("   ❌ No operating hours defined!")
    else:
        for oh in op_hours:
            day = DAY_NAMES[oh.day_of_week]
            if oh.is_closed:
                print(f"   {day}: CLOSED")
            else:
                open_str = f"{oh.open_hours_start.strftime('%H:%M')}-{oh.open_hours_end.strftime('%H:%M')}"
                
                if oh.training_disabled:
                    train_str = "DISABLED"
                elif oh.training_start and oh.training_end:
                    train_str = f"{oh.training_start.strftime('%H:%M')}-{oh.training_end.strftime('%H:%M')}"
                else:
                    train_str = "NOT SET (null)"
                
                print(f"   {day}: Open {open_str}, Training {train_str}")
    
    # =========================================================================
    # 2. Shift Requirements by Day
    # =========================================================================
    print("\n" + "-" * 40)
    print("2. SHIFT REQUIREMENTS BY DAY")
    print("-" * 40)
    
    for day in range(7):
        day_name = DAY_NAMES[day]
        reqs = ShiftRequirement.objects.filter(semester=semester, day_of_week=day).order_by('time_start')
        
        if not reqs.exists():
            print(f"   {day_name}: No requirements")
            continue
        
        # Group by time slot
        time_slots = {}
        for req in reqs:
            key = f"{req.time_start.strftime('%H:%M')}-{req.time_end.strftime('%H:%M')}"
            if key not in time_slots:
                time_slots[key] = {'hosts': 0, 'floaters': 0, 'locations': []}
            time_slots[key]['hosts'] += req.hosts_required
            time_slots[key]['floaters'] += req.floaters_required
            if req.location:
                time_slots[key]['locations'].append(req.location.name)
            elif req.location_group:
                time_slots[key]['locations'].append(f"[{req.location_group.name}]")
        
        print(f"   {day_name}:")
        for slot, data in sorted(time_slots.items()):
            print(f"      {slot}: {data['hosts']} hosts, {data['floaters']} floaters")
    
    # =========================================================================
    # 3. Machine Counts (for training)
    # =========================================================================
    print("\n" + "-" * 40)
    print("3. MACHINE COUNTS (for training slots)")
    print("-" * 40)
    
    try:
        from machines.models import Machine
        total = Machine.objects.filter(is_active=True).count()
        print(f"   Total active machines: {total}")
        
        if total > 0:
            counts = Machine.objects.filter(is_active=True).values('category').annotate(count=Count('id'))
            for c in counts:
                print(f"      {c['category']}: {c['count']} machines")
        else:
            print("   ⚠️ No active machines - training will NOT be scheduled!")
    except Exception as e:
        print(f"   ❌ Error loading machines: {e}")
    
    # =========================================================================
    # 4. Team Members
    # =========================================================================
    print("\n" + "-" * 40)
    print("4. TEAM MEMBERS")
    print("-" * 40)
    
    profiles = TeamMemberProfile.objects.all()
    total = profiles.count()
    trainers = profiles.filter(is_trainer=True).count()
    team_leads = profiles.filter(is_team_lead=True).count()
    
    print(f"   Total: {total}")
    print(f"   Trainers: {trainers}")
    print(f"   Team Leads: {team_leads}")
    
    # By team/category
    print("\n   By Team:")
    by_team = profiles.values('team').annotate(count=Count('id')).order_by('team')
    for t in by_team:
        team_name = t['team'] or '(no team/floater)'
        print(f"      {team_name}: {t['count']}")
    
    # =========================================================================
    # 5. Friday Specific Check
    # =========================================================================
    print("\n" + "-" * 40)
    print("5. FRIDAY DETAILED CHECK")
    print("-" * 40)
    
    friday_reqs = ShiftRequirement.objects.filter(
        semester=semester, 
        day_of_week=4
    ).order_by('time_start')
    
    if not friday_reqs.exists():
        print("   ❌ No Friday requirements found!")
    else:
        print("   Requirements:")
        for req in friday_reqs:
            loc = req.location.name if req.location else (
                f"[{req.location_group.name}]" if req.location_group else "Floater"
            )
            print(f"      {req.time_start.strftime('%H:%M')}-{req.time_end.strftime('%H:%M')}: "
                  f"{req.hosts_required}H/{req.floaters_required}F @ {loc}")
    
    # Check if 9am slot exists
    has_9am = friday_reqs.filter(time_start__hour=9).exists()
    if not has_9am:
        print("\n   ⚠️ WARNING: No 9:00 AM slot on Friday!")
        print("   → Re-run generate_test_requirements.py to fix this")
    
    print("\n" + "=" * 60)
    print("DIAGNOSTICS COMPLETE")
    print("=" * 60 + "\n")


# Run it
run_diagnostics()