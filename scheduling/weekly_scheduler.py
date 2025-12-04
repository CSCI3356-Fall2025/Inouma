"""
Weekly Auto-Scheduler for The Hatchery - v4 COMPLETE REWRITE
=============================================================

SIMPLE, CORRECT APPROACH:
1. Each person has a weekly hour budget (e.g., 10 hours)
2. We schedule shifts until their budget is used up
3. NO ONE can exceed their budget
4. NO duplicate shifts (same person, same time)

The math:
- 50 employees × 12 avg hours = 600 total hours/week
- That's ~600 one-hour shifts OR ~300 two-hour shifts per week
- Over 3 weeks = ~1800 shifts total (NOT 4000+)
"""

from datetime import datetime, timedelta, time, date as dt_date
from collections import defaultdict
from django.db.models import Count
import math

from .models import (
    Semester, DailyOperatingHours, ShiftRequirement, 
    TeamMemberProfile, Unavailability, Shift
)


class WeeklyScheduler:
    """Simple, correct weekly scheduler"""
    
    DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # Shift lengths by preference
    SHIFT_LENGTHS = {
        'few_long': [3, 4, 2],       # Prefer 3-4 hour shifts
        'many_short': [1, 2],         # Prefer 1-2 hour shifts
        'no_preference': [2, 1, 3]    # Default to 2 hour shifts
    }
    
    def __init__(self, semester):
        self.semester = semester
        self.team_members = []
        self.unavailability_map = {}
        self.machine_counts = {}
        self.conflicts = []
        
        # CORE TRACKING - simple and correct
        self.weekly_shifts = []                    # List of shift dicts
        self.hours_remaining = {}                  # {user_id: hours_left}
        self.person_shifts = defaultdict(list)     # {user_id: [shift_dicts]}
        self.slot_occupancy = defaultdict(set)     # {(day, hour): set of user_ids}
        
    def run(self):
        """Main entry point"""
        print(f"\n{'='*60}")
        print(f"🚀 WEEKLY SCHEDULER v4 for {self.semester.name}")
        print(f"{'='*60}\n")
        
        if not self._load_data():
            return self._error_result('Failed to load data')
        
        self._clear_existing_shifts()
        
        # Calculate expected totals
        total_hours_available = sum(self.hours_remaining.values())
        print(f"📊 Total weekly hours to schedule: {total_hours_available}")
        print(f"   (This should result in ~{int(total_hours_available/2)} two-hour shifts per week)\n")
        
        # Phase 1: Required shifts (open hours, floaters)
        print("📅 Phase 1: Scheduling required shifts...\n")
        required_count = self._schedule_required_shifts()
        print(f"   ✓ Scheduled {required_count} required shifts\n")
        
        # Phase 2: Training shifts
        print("📅 Phase 2: Scheduling training shifts...\n")
        training_count = self._schedule_training_shifts()
        print(f"   ✓ Scheduled {training_count} training shifts\n")
        
        # Validate
        self._validate()
        
        # Summary
        self._print_summary()
        
        # Replicate to semester
        all_shifts = self._replicate_to_semester()
        saved = self._save_to_database(all_shifts)
        
        return {
            'success': len(self.conflicts) == 0,
            'shifts_created': saved,
            'conflicts': self.conflicts,
            'message': f"Created {len(self.weekly_shifts)} weekly shifts, {saved} total"
        }
    
    def _load_data(self):
        """Load team members and their hour budgets"""
        print("📊 Loading data...")
        
        self.team_members = list(
            TeamMemberProfile.objects.select_related('user')
            .filter(is_active=True)
        )
        
        if not self.team_members:
            print("   ❌ No active team members!")
            return False
        
        # Initialize hours remaining for each person
        for tm in self.team_members:
            expected = tm.get_expected_hours(self.semester)
            self.hours_remaining[tm.user_id] = expected
        
        total = sum(self.hours_remaining.values())
        print(f"   ✓ {len(self.team_members)} team members, {total} total hours/week")
        
        # Load unavailability
        for unav in Unavailability.objects.filter(semester=self.semester, status='approved'):
            if unav.user_id not in self.unavailability_map:
                self.unavailability_map[unav.user_id] = []
            self.unavailability_map[unav.user_id].append(
                (unav.day_of_week, unav.start_time, unav.end_time)
            )
        
        # Load machine counts for training limits
        self._load_machine_counts()
        
        return True
    
    def _load_machine_counts(self):
        """Load machine counts for training capacity"""
        try:
            from machines.models import Machine
            
            counts = Machine.objects.values('category').annotate(count=Count('id'))
            for item in counts:
                if item['category']:
                    self.machine_counts[item['category']] = item['count']
            
            # Add categories from trainers
            for tm in self.team_members:
                if tm.is_trainer and tm.team and tm.team not in self.machine_counts:
                    self.machine_counts[tm.team] = 2
                    
        except Exception as e:
            print(f"   ⚠️ Could not load machines: {e}")
    
    def _clear_existing_shifts(self):
        """Clear existing scheduled shifts"""
        deleted, _ = Shift.objects.filter(
            semester=self.semester,
            status='scheduled'
        ).delete()
        if deleted:
            print(f"🗑️ Cleared {deleted} existing shifts\n")
    
    def _schedule_required_shifts(self):
        """Schedule open hours and floater shifts"""
        count = 0
        
        for day in range(7):
            try:
                op_hours = DailyOperatingHours.objects.get(
                    semester=self.semester,
                    day_of_week=day
                )
                if op_hours.is_closed:
                    continue
            except DailyOperatingHours.DoesNotExist:
                continue
            
            # Get requirements for this day
            requirements = ShiftRequirement.objects.filter(
                semester=self.semester,
                day_of_week=day
            ).select_related('location', 'location_group')
            
            for req in requirements:
                # Schedule hosts
                for _ in range(req.hosts_required):
                    if self._create_shift(
                        day=day,
                        start=req.time_start,
                        end=req.time_end,
                        shift_type='open_hours',
                        location=req.location,
                        location_group=req.location_group
                    ):
                        count += 1
                
                # Schedule floaters
                for _ in range(req.floaters_required):
                    if self._create_shift(
                        day=day,
                        start=req.time_start,
                        end=req.time_end,
                        shift_type='floater'
                    ):
                        count += 1
        
        return count
    
    def _schedule_training_shifts(self):
        """Schedule training shifts for trainers with remaining hours"""
        count = 0
        
        # Get training windows per day
        training_windows = {}
        for day in range(7):
            try:
                op = DailyOperatingHours.objects.get(semester=self.semester, day_of_week=day)
                if not op.is_closed and not op.training_disabled and op.training_start and op.training_end:
                    training_windows[day] = (op.training_start.hour, op.training_end.hour)
            except DailyOperatingHours.DoesNotExist:
                pass
        
        if not training_windows:
            print("   No training windows defined")
            return 0
        
        # Track training slots: {(day, hour, category): count}
        training_slots = defaultdict(int)
        
        def get_max_trainers(category):
            """Max 30% of machines for training"""
            machines = self.machine_counts.get(category, 2)
            return max(1, int(machines * 0.3))
        
        # Keep scheduling until no one needs hours
        max_iterations = 1000
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Get trainers who need hours, sorted by most remaining
            trainers = [
                tm for tm in self.team_members
                if tm.is_trainer and tm.team and self.hours_remaining.get(tm.user_id, 0) >= 1
            ]
            trainers.sort(key=lambda tm: -self.hours_remaining.get(tm.user_id, 0))
            
            if not trainers:
                break
            
            made_progress = False
            
            for tm in trainers:
                remaining = self.hours_remaining.get(tm.user_id, 0)
                if remaining < 1:
                    continue
                
                # Get preferred shift lengths
                pref = tm.shift_preference or 'no_preference'
                lengths = self.SHIFT_LENGTHS.get(pref, [2, 1, 3])
                
                # Try to find a slot
                slot = self._find_training_slot(
                    tm, training_windows, training_slots, lengths, get_max_trainers
                )
                
                if slot:
                    day, start_hour, duration = slot
                    start_time = time(hour=start_hour)
                    end_time = time(hour=start_hour + duration)
                    
                    if self._create_shift(
                        day=day,
                        start=start_time,
                        end=end_time,
                        shift_type='training',
                        team_category=tm.team,
                        specific_user=tm
                    ):
                        # Mark training slot usage
                        for h in range(start_hour, start_hour + duration):
                            training_slots[(day, h, tm.team)] += 1
                        
                        count += 1
                        made_progress = True
            
            if not made_progress:
                break
        
        return count
    
    def _find_training_slot(self, tm, windows, slots, lengths, get_max_trainers):
        """Find best training slot for this person"""
        user_id = tm.user_id
        category = tm.team
        remaining = self.hours_remaining.get(user_id, 0)
        
        # Count shifts per day for this person (for spreading)
        shifts_per_day = defaultdict(int)
        for shift in self.person_shifts[user_id]:
            shifts_per_day[shift['day_of_week']] += 1
        
        best = None
        best_score = float('inf')
        
        # Try each day
        for day, (window_start, window_end) in windows.items():
            # Try each shift length
            for length in lengths:
                if length > remaining:
                    continue
                
                # Try each starting hour
                for start_hour in range(window_start, window_end - length + 1):
                    start_t = time(hour=start_hour)
                    end_t = time(hour=start_hour + length)
                    
                    # Check availability
                    if not self._is_available(user_id, day, start_t, end_t):
                        continue
                    
                    # Check machine capacity
                    max_trainers = get_max_trainers(category)
                    can_fit = True
                    for h in range(start_hour, start_hour + length):
                        if slots[(day, h, category)] >= max_trainers:
                            can_fit = False
                            break
                    
                    if not can_fit:
                        continue
                    
                    # Score: prefer days with fewer shifts, then earlier times
                    score = shifts_per_day[day] * 100 + start_hour
                    
                    if score < best_score:
                        best_score = score
                        best = (day, start_hour, length)
        
        return best
    
    def _create_shift(self, day, start, end, shift_type, location=None, 
                      location_group=None, team_category=None, specific_user=None):
        """
        Create a shift and assign to best available person.
        Returns True if successful.
        """
        duration = self._hours_between(start, end)
        
        if specific_user:
            # Assign to specific user (for training)
            person = specific_user
            if not self._is_available(person.user_id, day, start, end):
                return False
        else:
            # Find best available person
            person = self._find_available_person(day, start, end, duration)
            if not person:
                return False
        
        # Create the shift
        shift = {
            'user_id': person.user_id,
            'day_of_week': day,
            'start_time': start,
            'end_time': end,
            'shift_type': shift_type,
            'location': location,
            'location_group': location_group,
            'team_category': team_category
        }
        
        self.weekly_shifts.append(shift)
        self.person_shifts[person.user_id].append(shift)
        
        # Deduct hours
        self.hours_remaining[person.user_id] -= duration
        
        # Mark slot occupancy
        for hour in range(start.hour, end.hour):
            self.slot_occupancy[(day, hour)].add(person.user_id)
        
        return True
    
    def _find_available_person(self, day, start, end, duration):
        """Find the best available person for a shift"""
        candidates = []
        
        for tm in self.team_members:
            remaining = self.hours_remaining.get(tm.user_id, 0)
            
            # Must have enough hours
            if remaining < duration:
                continue
            
            # Must be available
            if not self._is_available(tm.user_id, day, start, end):
                continue
            
            candidates.append((tm, remaining))
        
        if not candidates:
            return None
        
        # Sort by most hours remaining (fair distribution)
        candidates.sort(key=lambda x: -x[1])
        return candidates[0][0]
    
    def _is_available(self, user_id, day, start, end):
        """Check if user is available for this slot"""
        
        # Check unavailability
        for (unav_day, unav_start, unav_end) in self.unavailability_map.get(user_id, []):
            if unav_day == day:
                if self._times_overlap(start, end, unav_start, unav_end):
                    return False
        
        # Check if already booked (prevent double-booking)
        for hour in range(start.hour, end.hour):
            if user_id in self.slot_occupancy[(day, hour)]:
                return False
        
        return True
    
    def _validate(self):
        """Validate the schedule"""
        print("🔍 Validating...")
        
        # Check for over-scheduled people
        issues = 0
        for tm in self.team_members:
            expected = tm.get_expected_hours(self.semester)
            remaining = self.hours_remaining.get(tm.user_id, 0)
            used = expected - remaining
            
            if used > expected + 0.1:  # Small tolerance for floating point
                print(f"   ❌ {tm.user.get_full_name()} over-scheduled: {used:.1f}/{expected} hrs")
                issues += 1
        
        # Check for double bookings
        for user_id, shifts in self.person_shifts.items():
            by_day = defaultdict(list)
            for s in shifts:
                by_day[s['day_of_week']].append(s)
            
            for day, day_shifts in by_day.items():
                for i, s1 in enumerate(day_shifts):
                    for s2 in day_shifts[i+1:]:
                        if self._times_overlap(s1['start_time'], s1['end_time'],
                                              s2['start_time'], s2['end_time']):
                            tm = next((t for t in self.team_members if t.user_id == user_id), None)
                            name = tm.user.get_full_name() if tm else user_id
                            print(f"   ❌ Double booking: {name} on {self.DAY_NAMES[day]}")
                            issues += 1
        
        if issues == 0:
            print("   ✓ No issues found")
        else:
            print(f"   ❌ {issues} issues found")
    
    def _print_summary(self):
        """Print schedule summary"""
        print(f"\n📊 Model Week Summary:")
        print(f"   Total shifts: {len(self.weekly_shifts)}")
        
        # By type
        by_type = defaultdict(int)
        for s in self.weekly_shifts:
            by_type[s['shift_type']] += 1
        for t, c in sorted(by_type.items()):
            print(f"   - {t}: {c}")
        
        # Hours per person
        print(f"\n   Hours scheduled per person:")
        for tm in sorted(self.team_members, key=lambda t: t.user.get_full_name()):
            expected = tm.get_expected_hours(self.semester)
            remaining = self.hours_remaining.get(tm.user_id, 0)
            used = expected - remaining
            pct = (used / expected * 100) if expected > 0 else 0
            
            if used > 0:
                status = "✓" if pct >= 80 else "⚠️" if pct >= 50 else "❌"
                pref = (tm.shift_preference or 'no_pref')[:8]
                print(f"      {tm.user.get_full_name()[:25]:25} {used:5.1f}/{expected:5.1f} ({pct:3.0f}%) [{pref}] {status}")
        
        # Total hours
        total_expected = sum(tm.get_expected_hours(self.semester) for tm in self.team_members)
        total_scheduled = sum(
            tm.get_expected_hours(self.semester) - self.hours_remaining.get(tm.user_id, 0)
            for tm in self.team_members
        )
        print(f"\n   Total: {total_scheduled:.1f}/{total_expected:.1f} hours scheduled ({total_scheduled/total_expected*100:.1f}%)")
    
    def _replicate_to_semester(self):
        """Replicate model week across semester"""
        print(f"\n🔄 Replicating across semester...")
        
        all_shifts = []
        current = self.semester.start_date
        
        # Find first Monday
        while current.weekday() != 0:
            current += timedelta(days=1)
        
        # Get holidays
        holidays = set()
        if self.semester.holidays:
            for h in self.semester.holidays:
                if isinstance(h, str):
                    holidays.add(h)
                elif isinstance(h, dict):
                    holidays.add(h.get('date', ''))
        
        weeks = 0
        while current <= self.semester.end_date:
            weeks += 1
            
            for day_offset in range(7):
                shift_date = current + timedelta(days=day_offset)
                
                if shift_date < self.semester.start_date or shift_date > self.semester.end_date:
                    continue
                if shift_date.isoformat() in holidays:
                    continue
                
                day_of_week = shift_date.weekday()
                
                for template in self.weekly_shifts:
                    if template['day_of_week'] == day_of_week:
                        all_shifts.append({**template, 'date': shift_date})
            
            current += timedelta(days=7)
        
        print(f"   ✓ {len(all_shifts)} shifts across {weeks} weeks")
        return all_shifts
    
    def _save_to_database(self, all_shifts):
        """Save to database"""
        print(f"\n💾 Saving...")
        
        objs = [
            Shift(
                semester=self.semester,
                user_id=s['user_id'],
                date=s['date'],
                start_time=s['start_time'],
                end_time=s['end_time'],
                shift_type=s['shift_type'],
                location=s.get('location'),
                location_group=s.get('location_group'),
                team_category=s.get('team_category') or '',
                status='scheduled'
            )
            for s in all_shifts
        ]
        
        Shift.objects.bulk_create(objs, batch_size=500)
        print(f"   ✓ Saved {len(objs)} shifts")
        return len(objs)
    
    def _hours_between(self, start, end):
        """Calculate hours between two times"""
        s = datetime.combine(dt_date.today(), start)
        e = datetime.combine(dt_date.today(), end)
        return (e - s).total_seconds() / 3600
    
    def _times_overlap(self, s1, e1, s2, e2):
        """Check if time ranges overlap"""
        return not (e1 <= s2 or s1 >= e2)
    
    def _error_result(self, msg):
        return {
            'success': False,
            'shifts_created': 0,
            'conflicts': [{'type': 'error', 'day': None, 'time': None, 'location': msg}],
            'message': msg
        }
