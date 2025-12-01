"""
Scheduler Debug Script - Step by Step
======================================
Run with: python manage.py shell < testing/debug_scheduler.py
"""

from datetime import time
from collections import defaultdict
from django.db.models import Count

from scheduling.models import (
    Semester, DailyOperatingHours, ShiftRequirement, 
    TeamMemberProfile, Unavailability, Shift
)

DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

def debug_scheduler():
    print("\n" + "=" * 60)
    print("SCHEDULER DEBUG - STEP BY STEP")
    print("=" * 60)
    
    semester = Semester.objects.filter(is_active=True).first()
    if not semester:
        print("❌ No active semester!")
        return
    
    print(f"\n📅 Semester: {semester.name}")
    
    # =========================================================================
    # Step 1: Check Team Members and their hours
    # =========================================================================
    print("\n" + "-" * 40)
    print("STEP 1: Team Members & Expected Hours")
    print("-" * 40)
    
    team_members = list(TeamMemberProfile.objects.select_related('user').all())
    print(f"   Total team members: {len(team_members)}")
    
    # Check expected hours
    hours_issues = []
    for tm in team_members[:10]:  # Sample first 10
        try:
            expected = tm.get_expected_hours(semester)
            max_hrs = tm.max_weekly_hours
            print(f"   {tm.user.email}: expected={expected}, max_weekly={max_hrs}")
        except Exception as e:
            hours_issues.append(f"{tm.user.email}: {e}")
            print(f"   {tm.user.email}: ERROR - {e}")
    
    if hours_issues:
        print(f"\n   ⚠️ {len(hours_issues)} members have hours issues")
    
    # =========================================================================
    # Step 2: Check Friday Requirements specifically
    # =========================================================================
    print("\n" + "-" * 40)
    print("STEP 2: Friday 9:00-13:00 Slot Analysis")
    print("-" * 40)
    
    friday_9am_reqs = ShiftRequirement.objects.filter(
        semester=semester,
        day_of_week=4,  # Friday
        time_start=time(9, 0)
    )
    
    print(f"   Friday 9am requirements: {friday_9am_reqs.count()}")
    for req in friday_9am_reqs:
        loc = req.location.name if req.location else (
            f"[Group: {req.location_group.name}]" if req.location_group else "Floater"
        )
        print(f"      {req.time_start}-{req.time_end}: {req.hosts_required}H/{req.floaters_required}F @ {loc}")
    
    # =========================================================================
    # Step 3: Check who's available Friday 9am
    # =========================================================================
    print("\n" + "-" * 40)
    print("STEP 3: Who's Available Friday 9:00-13:00?")
    print("-" * 40)
    
    # Get Friday unavailabilities
    friday_unavail = Unavailability.objects.filter(
        semester=semester,
        day_of_week=4
    )
    
    unavail_map = defaultdict(list)
    for u in friday_unavail:
        unavail_map[u.user_id].append((u.start_time, u.end_time, u.reason))
    
    # Check each team member
    available_count = 0
    unavailable_count = 0
    
    slot_start = time(9, 0)
    slot_end = time(13, 0)
    
    available_members = []
    unavailable_members = []
    
    for tm in team_members:
        user_unavail = unavail_map.get(tm.user_id, [])
        
        is_available = True
        block_reason = None
        
        for (start, end, reason) in user_unavail:
            # Check overlap
            if start < slot_end and end > slot_start:
                is_available = False
                block_reason = f"Unavailable {start}-{end} ({reason})"
                break
        
        if is_available:
            available_count += 1
            available_members.append(tm)
        else:
            unavailable_count += 1
            unavailable_members.append((tm, block_reason))
    
    print(f"   Available for Friday 9-13: {available_count}")
    print(f"   Unavailable: {unavailable_count}")
    
    print(f"\n   First 10 available members:")
    for tm in available_members[:10]:
        try:
            expected = tm.get_expected_hours(semester)
        except:
            expected = "ERROR"
        print(f"      {tm.user.first_name} {tm.user.last_name} ({tm.team or 'floater'}) - {expected} hrs/wk")
    
    if unavailable_members:
        print(f"\n   First 5 unavailable members:")
        for tm, reason in unavailable_members[:5]:
            print(f"      {tm.user.first_name} {tm.user.last_name}: {reason}")
    
    # =========================================================================
    # Step 4: Check existing shifts for Friday
    # =========================================================================
    print("\n" + "-" * 40)
    print("STEP 4: Existing Friday Shifts in Database")
    print("-" * 40)
    
    friday_shifts = Shift.objects.filter(
        semester=semester,
        day_of_week=4
    ).order_by('start_time')
    
    print(f"   Total Friday shifts: {friday_shifts.count()}")
    
    # Group by time
    by_time = defaultdict(list)
    for s in friday_shifts:
        key = f"{s.start_time.strftime('%H:%M')}-{s.end_time.strftime('%H:%M')}"
        by_time[key].append(s)
    
    for time_slot, shifts in sorted(by_time.items()):
        print(f"\n   {time_slot}: {len(shifts)} shifts")
        for s in shifts[:3]:
            loc = s.location.name if s.location else (
                s.location_group.name if s.location_group else "Floater"
            )
            user_name = s.user.email if s.user else "UNASSIGNED"
            print(f"      {s.shift_type} @ {loc} - {user_name}")
        if len(shifts) > 3:
            print(f"      ... and {len(shifts) - 3} more")
    
    # Check for 9am slot specifically
    shifts_9am = [s for s in friday_shifts if s.start_time.hour == 9]
    if not shifts_9am:
        print("\n   ⚠️ NO SHIFTS AT 9:00 AM ON FRIDAY!")
        print("   This is the bug - scheduler isn't filling this slot")
    
    # =========================================================================
    # Step 5: Simulate Assignment
    # =========================================================================
    print("\n" + "-" * 40)
    print("STEP 5: Simulated Assignment for Friday 9am")
    print("-" * 40)
    
    # Try to assign each requirement
    hours_used = defaultdict(float)
    
    for req in friday_9am_reqs:
        loc = req.location.name if req.location else (
            f"[{req.location_group.name}]" if req.location_group else "Floater"
        )
        
        print(f"\n   Trying to fill: {loc} ({req.hosts_required} hosts needed)")
        
        # Find available members who haven't exceeded hours
        candidates = []
        for tm in available_members:
            try:
                expected = tm.get_expected_hours(semester)
                if expected is None:
                    expected = tm.max_weekly_hours or 10
            except:
                expected = tm.max_weekly_hours or 10
            
            duration = 4  # 9am to 1pm
            if hours_used[tm.user_id] + duration <= expected:
                candidates.append((tm, expected, hours_used[tm.user_id]))
        
        if candidates:
            # Sort by hours used
            candidates.sort(key=lambda x: x[2])
            tm, expected, used = candidates[0]
            print(f"      ✓ Could assign: {tm.user.first_name} {tm.user.last_name}")
            print(f"        Hours: {used}/{expected}, adding 4 = {used + 4}")
            hours_used[tm.user_id] += 4
        else:
            print(f"      ❌ NO CANDIDATES AVAILABLE!")
            print(f"         Available members: {len(available_members)}")
            print(f"         All at max hours already")
    
    print("\n" + "=" * 60)
    print("DEBUG COMPLETE")
    print("=" * 60)
    print("\nIf Friday 9am slots show as fillable but aren't being filled,")
    print("the issue is likely in the scheduler's _assign_shift logic or")
    print("the order of operations.")
    print()


# Run
debug_scheduler()