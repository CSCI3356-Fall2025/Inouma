"""
The Hatchery Weekly Auto-Scheduler
==================================

Creates a model week of shifts and replicates across the semester.

Three shift types (priority order):
1. Open Hours - Staff specific locations during public hours
2. Floaters - Roaming support staff
3. Training - Trainers conduct sessions (fills remaining hours)

Key invariant: hours_remaining is ALWAYS decremented when a shift is created.
This prevents over-scheduling.
"""

from datetime import datetime, timedelta, time, date
from collections import defaultdict
from django.db.models import Count

from .models import (
    Semester, DailyOperatingHours, ShiftRequirement,
    TeamMemberProfile, Unavailability, Shift
)


class WeeklyScheduler:
    """
    Weekly auto-scheduler that respects hour limits and prevents double-booking.
    """
    
    DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    def __init__(self, semester):
        self.semester = semester
        
        # Data loaded from DB
        self.team_members = []
        self.unavailability = {}      # {user_id: [(day, start, end), ...]}
        self.machine_counts = {}      # {category: count}
        
        # Core tracking structures
        self.hours_remaining = {}     # {user_id: float} - DECREMENTED on each shift
        self.person_shifts = {}       # {user_id: [shift_dict, ...]}
        self.slot_occupancy = {}      # {(day, hour): set(user_ids)}
        self.training_usage = {}      # {(day, hour, category): int}
        
        # Output
        self.weekly_shifts = []       # Model week template
        self.conflicts = []           # Unfilled requirements
    
    def run(self):
        """Main entry point."""
        print(f"\n{'='*60}")
        print(f"WEEKLY SCHEDULER for {self.semester.name}")
        print(f"{'='*60}\n")
        
        # Phase 0: Load data
        if not self._load_data():
            return self._error_result("Failed to load data")
        
        # Print expected math
        total_hours = sum(self.hours_remaining.values())
        print(f"Expected weekly hours: {total_hours}")
        print(f"Expected weekly shifts (avg 2hr): ~{int(total_hours / 2)}\n")
        
        # Phase 1: Schedule required shifts
        print("Phase 1: Scheduling required shifts (open hours + floaters)...")
        required_filled, required_total = self._schedule_required_shifts()
        print(f"  Filled {required_filled}/{required_total} required slots\n")
        
        # Phase 2: Schedule training shifts
        print("Phase 2: Scheduling training shifts...")
        training_count = self._schedule_training_shifts()
        print(f"  Created {training_count} training shifts\n")
        
        # Validate
        errors = self._validate()
        if errors:
            print("VALIDATION ERRORS:")
            for e in errors:
                print(f"  - {e}")
        
        # Summary
        self._print_summary()
        
        # Save model week (Week 0) first
        model_week_saved = self._save_model_week()
        
        # Replicate and save full semester
        all_shifts = self._replicate_to_semester()
        saved = self._save_to_database(all_shifts)
        
        return {
            'success': len(self.conflicts) == 0 and len(errors) == 0,
            'shifts_created': saved,
            'weekly_shifts': len(self.weekly_shifts),
            'model_week_shifts': model_week_saved,
            'conflicts': self.conflicts,
            'message': f"Created {len(self.weekly_shifts)} weekly shifts, {saved} total across semester"
        }
    
    # =========================================================================
    # PHASE 0: LOAD DATA
    # =========================================================================
    
    def _load_data(self):
        """Load all required data from database."""
        print("Loading data...")
        
        # Load team members
        self.team_members = list(
            TeamMemberProfile.objects.filter(is_active=True).select_related('user')
        )
        
        if not self.team_members:
            print("  ERROR: No active team members")
            return False
        
        # Initialize hours remaining
        for tm in self.team_members:
            hours = tm.get_expected_hours(self.semester)
            self.hours_remaining[tm.user_id] = float(hours)
            self.person_shifts[tm.user_id] = []
        
        print(f"  {len(self.team_members)} team members")
        print(f"  {sum(self.hours_remaining.values())} total weekly hours")
        
        # Load unavailability
        for u in Unavailability.objects.filter(semester=self.semester):
            if u.user_id not in self.unavailability:
                self.unavailability[u.user_id] = []
            self.unavailability[u.user_id].append((u.day_of_week, u.start_time, u.end_time))
        
        print(f"  {len(self.unavailability)} members with unavailability")
        
        # Load machine counts
        try:
            from machines.models import Machine
            counts = Machine.objects.filter(is_active=True).values('category').annotate(count=Count('id'))
            for item in counts:
                if item['category']:
                    self.machine_counts[item['category']] = item['count']
        except Exception:
            pass
        
        # Ensure all trainer categories have a count
        for tm in self.team_members:
            if tm.is_trainer and tm.team and tm.team not in self.machine_counts:
                self.machine_counts[tm.team] = 2
        
        print(f"  {len(self.machine_counts)} equipment categories")
        
        # Clear existing scheduled shifts
        deleted, _ = Shift.objects.filter(semester=self.semester, status='scheduled').delete()
        if deleted:
            print(f"  Cleared {deleted} existing shifts")
        
        print()
        return True
    
    # =========================================================================
    # PHASE 1: REQUIRED SHIFTS (OPEN HOURS + FLOATERS)
    # =========================================================================
    
    def _schedule_required_shifts(self):
        """
        Schedule all required open hours and floater shifts.
        
        For each requirement, we need to ensure `hosts_required` people cover
        every hour in the time block. We fill one "lane" at a time.
        """
        total_slots = 0
        filled_slots = 0
        
        requirements = ShiftRequirement.objects.filter(
            semester=self.semester
        ).select_related('location', 'location_group').order_by('day_of_week', 'time_start')
        
        for req in requirements:
            day = req.day_of_week
            block_start = req.time_start
            block_end = req.time_end
            block_hours = int(self._hours_between(block_start, block_end))
            
            # Process hosts
            for lane in range(req.hosts_required):
                total_slots += block_hours
                hours_filled = self._fill_lane(
                    day=day,
                    block_start=block_start,
                    block_end=block_end,
                    shift_type='open_hours',
                    location=req.location,
                    location_group=req.location_group
                )
                filled_slots += hours_filled
                
                if hours_filled < block_hours:
                    unfilled = block_hours - hours_filled
                    self.conflicts.append({
                        'type': 'unfilled_host',
                        'day': self.DAY_NAMES[day],
                        'time': f"{block_start}-{block_end}",
                        'location': str(req.location or req.location_group or 'Unknown'),
                        'hours_missing': unfilled
                    })
            
            # Process floaters
            for lane in range(req.floaters_required):
                total_slots += block_hours
                hours_filled = self._fill_lane(
                    day=day,
                    block_start=block_start,
                    block_end=block_end,
                    shift_type='floater',
                    location=None,
                    location_group=None
                )
                filled_slots += hours_filled
                
                if hours_filled < block_hours:
                    unfilled = block_hours - hours_filled
                    self.conflicts.append({
                        'type': 'unfilled_floater',
                        'day': self.DAY_NAMES[day],
                        'time': f"{block_start}-{block_end}",
                        'location': 'N/A',
                        'hours_missing': unfilled
                    })
        
        return filled_slots, total_slots
    
    def _fill_lane(self, day, block_start, block_end, shift_type, location, location_group):
        """
        Fill one "lane" of a time block with shifts.
        
        A lane represents one person's coverage. If we need 2 hosts from 9-13,
        we call this twice - once for each lane.
        
        Returns the number of hours successfully filled.
        """
        hours_filled = 0
        current_time = block_start
        
        while current_time < block_end:
            remaining_hours = self._hours_between(current_time, block_end)
            
            if remaining_hours < 1:
                break
            
            # Find someone to cover starting at current_time
            person, duration = self._find_person_for_required(
                day=day,
                start=current_time,
                max_duration=remaining_hours
            )
            
            if person is None:
                # No one available for this hour, skip it and try next hour
                current_time = self._add_hours(current_time, 1)
                continue
            
            # Create the shift
            shift_end = self._add_hours(current_time, duration)
            self._create_shift(
                user_id=person.user_id,
                day=day,
                start=current_time,
                end=shift_end,
                shift_type=shift_type,
                location=location,
                location_group=location_group,
                team_category=None
            )
            
            hours_filled += duration
            current_time = shift_end  # Move to end of this shift
        
        return hours_filled
    
    def _find_person_for_required(self, day, start, max_duration):
        """
        Find best person for a required shift slot (open hours or floater).
        
        PRIORITY ORDER:
        1. Non-trainers first (they can ONLY do open hours/floater)
        2. Then trainers (who can also do training shifts)
        
        Within each group, prefer those with most hours remaining.
        
        Preference rules for duration:
        - few_long: prefer 4hr, fallback 3hr
        - many_short: prefer 2hr, fallback 1hr
        - no_preference: prefer 4hr, 3hr, 2hr, 1hr (longest that fits)
        
        Returns (TeamMemberProfile, duration) or (None, 0)
        """
        non_trainer_candidates = []
        trainer_candidates = []
        
        for tm in self.team_members:
            remaining_hours = self.hours_remaining.get(tm.user_id, 0)
            
            if remaining_hours < 1:
                continue
            
            # Determine preferred durations
            pref = tm.shift_preference or 'no_preference'
            if pref == 'few_long':
                preferred_durations = [4, 3]
            elif pref == 'many_short':
                preferred_durations = [2, 1]
            else:
                preferred_durations = [4, 3, 2, 1]
            
            # Find best fitting duration for this person
            for duration in preferred_durations:
                if duration > max_duration:
                    continue
                if duration > remaining_hours:
                    continue
                
                end_time = self._add_hours(start, duration)
                
                if self._is_available(tm.user_id, day, start, end_time):
                    # Separate into trainer vs non-trainer buckets
                    if tm.is_trainer:
                        trainer_candidates.append((tm, duration, remaining_hours))
                    else:
                        non_trainer_candidates.append((tm, duration, remaining_hours))
                    break  # Found best duration for this person
        
        # Sort each group by most hours remaining (fair distribution within group)
        non_trainer_candidates.sort(key=lambda x: -x[2])
        trainer_candidates.sort(key=lambda x: -x[2])
        
        # Prioritize non-trainers - they can ONLY do these shifts
        if non_trainer_candidates:
            return non_trainer_candidates[0][0], non_trainer_candidates[0][1]
        
        # Fall back to trainers
        if trainer_candidates:
            return trainer_candidates[0][0], trainer_candidates[0][1]
        
        return None, 0
    
    # =========================================================================
    # PHASE 2: TRAINING SHIFTS
    # =========================================================================
    
    def _schedule_training_shifts(self):
        """
        Fill remaining hours with training shifts for trainers.
        """
        training_count = 0
        
        # Get training windows per day
        training_windows = {}
        for day in range(7):
            try:
                op = DailyOperatingHours.objects.get(semester=self.semester, day_of_week=day)
                if not op.is_closed and not op.training_disabled and op.training_start and op.training_end:
                    training_windows[day] = (op.training_start.hour, op.training_end.hour)
            except DailyOperatingHours.DoesNotExist:
                continue
        
        if not training_windows:
            print("  No training windows configured")
            return 0
        
        # Keep scheduling until no progress
        max_iterations = 500
        
        for iteration in range(max_iterations):
            # Get trainers who need hours, sorted by most remaining first
            trainers = [
                tm for tm in self.team_members
                if tm.is_trainer and tm.team and self.hours_remaining.get(tm.user_id, 0) >= 1
            ]
            
            if not trainers:
                break
            
            # Sort by most hours remaining
            trainers.sort(key=lambda tm: -self.hours_remaining.get(tm.user_id, 0))
            
            made_progress = False
            
            for tm in trainers:
                remaining = self.hours_remaining.get(tm.user_id, 0)
                if remaining < 1:
                    continue
                
                # Preferred durations: 2hr default, 1hr fallback
                durations = [2, 1] if remaining >= 2 else [1]
                
                slot = self._find_training_slot(tm, training_windows, durations)
                
                if slot:
                    day, start_time, duration = slot
                    end_time = self._add_hours(start_time, duration)
                    
                    self._create_shift(
                        user_id=tm.user_id,
                        day=day,
                        start=start_time,
                        end=end_time,
                        shift_type='training',
                        location=None,
                        location_group=None,
                        team_category=tm.team
                    )
                    
                    # Record training usage for capacity tracking
                    for h in range(start_time.hour, end_time.hour):
                        key = (day, h, tm.team)
                        self.training_usage[key] = self.training_usage.get(key, 0) + 1
                    
                    training_count += 1
                    made_progress = True
                    break  # Re-sort trainers after each assignment
            
            if not made_progress:
                break
        
        return training_count
    
    def _find_training_slot(self, tm, windows, durations):
        """
        Find best training slot for a trainer.
        """
        category = tm.team
        max_trainers = self._get_max_trainers(category)
        
        # Count existing shifts per day for this person
        shifts_per_day = defaultdict(int)
        for shift in self.person_shifts.get(tm.user_id, []):
            shifts_per_day[shift['day_of_week']] += 1
        
        best_slot = None
        best_score = float('inf')
        
        for day, (window_start, window_end) in windows.items():
            for duration in durations:
                for start_hour in range(window_start, window_end - duration + 1):
                    start_time = time(hour=start_hour)
                    end_time = time(hour=start_hour + duration)
                    
                    # Check personal availability
                    if not self._is_available(tm.user_id, day, start_time, end_time):
                        continue
                    
                    # Check machine capacity
                    if not self._can_add_training(day, start_hour, duration, category, max_trainers):
                        continue
                    
                    # Score: prefer days with fewer shifts, then earlier times
                    score = shifts_per_day[day] * 100 + start_hour
                    
                    if score < best_score:
                        best_score = score
                        best_slot = (day, start_time, duration)
        
        return best_slot
    
    def _get_max_trainers(self, category):
        """Max 30% of machines can be used for training per hour."""
        machine_count = self.machine_counts.get(category, 2)
        return max(1, int(machine_count * 0.3))
    
    def _can_add_training(self, day, start_hour, duration, category, max_trainers):
        """Check if adding a trainer would exceed 30% capacity."""
        for h in range(start_hour, start_hour + duration):
            current = self.training_usage.get((day, h, category), 0)
            if current >= max_trainers:
                return False
        return True
    
    # =========================================================================
    # CORE HELPERS
    # =========================================================================
    
    def _is_available(self, user_id, day, start_time, end_time):
        """
        Check if user is available for a proposed shift.
        
        Checks:
        1. Not marked unavailable
        2. Not already scheduled (no double-booking)
        """
        # Check unavailability entries
        for (u_day, u_start, u_end) in self.unavailability.get(user_id, []):
            if u_day == day:
                # Overlap check
                if start_time < u_end and end_time > u_start:
                    return False
        
        # Check existing shifts (prevent double-booking)
        for existing_shift in self.person_shifts.get(user_id, []):
            if existing_shift['day_of_week'] == day:
                existing_start = existing_shift['start_time']
                existing_end = existing_shift['end_time']
                
                # Overlap check
                if start_time < existing_end and end_time > existing_start:
                    return False
        
        return True
    
    def _create_shift(self, user_id, day, start, end, shift_type, location=None, location_group=None, team_category=None):
        """
        Create a shift and update ALL tracking structures.
        
        This is the ONLY place shifts are created.
        """
        duration = self._hours_between(start, end)
        
        shift = {
            'user_id': user_id,
            'day_of_week': day,
            'start_time': start,
            'end_time': end,
            'shift_type': shift_type,
            'location': location,
            'location_group': location_group,
            'team_category': team_category
        }
        
        # Add to model week
        self.weekly_shifts.append(shift)
        
        # Track per person
        self.person_shifts[user_id].append(shift)
        
        # CRITICAL: Deduct hours
        self.hours_remaining[user_id] -= duration
        
        # Mark slot occupancy
        for hour in range(start.hour, end.hour):
            key = (day, hour)
            if key not in self.slot_occupancy:
                self.slot_occupancy[key] = set()
            self.slot_occupancy[key].add(user_id)
    
    def _hours_between(self, start, end):
        """Calculate hours between two time objects."""
        start_dt = datetime.combine(date.today(), start)
        end_dt = datetime.combine(date.today(), end)
        return (end_dt - start_dt).total_seconds() / 3600
    
    def _add_hours(self, t, hours):
        """Add hours to a time object, return new time."""
        dt = datetime.combine(date.today(), t) + timedelta(hours=int(hours))
        return dt.time()
    
    # =========================================================================
    # VALIDATION
    # =========================================================================
    
    def _validate(self):
        """Validate the schedule before saving."""
        errors = []
        
        # Check no one exceeded their hours
        for tm in self.team_members:
            expected = float(tm.get_expected_hours(self.semester))
            remaining = self.hours_remaining.get(tm.user_id, 0)
            used = expected - remaining
            
            if used > expected + 0.1:
                errors.append(f"{tm.user.get_full_name()} over-scheduled: {used:.1f}/{expected:.1f} hrs")
        
        # Check no double-bookings
        for user_id, shifts in self.person_shifts.items():
            by_day = defaultdict(list)
            for s in shifts:
                by_day[s['day_of_week']].append(s)
            
            for day, day_shifts in by_day.items():
                for i, s1 in enumerate(day_shifts):
                    for s2 in day_shifts[i+1:]:
                        if s1['start_time'] < s2['end_time'] and s1['end_time'] > s2['start_time']:
                            tm = next((t for t in self.team_members if t.user_id == user_id), None)
                            name = tm.user.get_full_name() if tm else f"User {user_id}"
                            errors.append(f"Double-booking: {name} on {self.DAY_NAMES[day]}")
        
        return errors
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    
    def _print_summary(self):
        """Print schedule summary."""
        print(f"\n{'='*60}")
        print("MODEL WEEK SUMMARY")
        print(f"{'='*60}")
        
        print(f"\nTotal shifts: {len(self.weekly_shifts)}")
        
        # By type
        by_type = defaultdict(int)
        for s in self.weekly_shifts:
            by_type[s['shift_type']] += 1
        
        for shift_type in ['open_hours', 'floater', 'training']:
            print(f"  {shift_type}: {by_type[shift_type]}")
        
        # By day
        print("\nShifts by day:")
        by_day = defaultdict(int)
        for s in self.weekly_shifts:
            by_day[s['day_of_week']] += 1
        
        for day in range(7):
            if by_day[day] > 0:
                print(f"  {self.DAY_NAMES[day]}: {by_day[day]}")
        
        # Hours per person
        print("\nHours per person:")
        scheduled_people = []
        for tm in self.team_members:
            expected = float(tm.get_expected_hours(self.semester))
            remaining = self.hours_remaining.get(tm.user_id, 0)
            used = expected - remaining
            
            if used > 0:
                pct = (used / expected * 100) if expected > 0 else 0
                status = "✓" if pct >= 80 else "⚠" if pct >= 50 else "✗"
                scheduled_people.append((tm.user.get_full_name(), used, expected, pct, status))
        
        scheduled_people.sort(key=lambda x: x[0])
        for name, used, expected, pct, status in scheduled_people:
            print(f"  {name[:30]:30} {used:5.1f}/{expected:5.1f} hrs ({pct:3.0f}%) {status}")
        
        # Totals
        total_expected = sum(float(tm.get_expected_hours(self.semester)) for tm in self.team_members)
        total_used = sum(
            float(tm.get_expected_hours(self.semester)) - self.hours_remaining.get(tm.user_id, 0)
            for tm in self.team_members
        )
        
        print(f"\nTotal: {total_used:.1f}/{total_expected:.1f} hours ({total_used/total_expected*100:.1f}%)")
        
        # Conflicts
        if self.conflicts:
            print(f"\nWARNING: {len(self.conflicts)} unfilled slots:")
            for c in self.conflicts[:10]:
                print(f"  {c['type']}: {c['day']} {c.get('time', '')} @ {c.get('location', 'N/A')}")
            if len(self.conflicts) > 10:
                print(f"  ... and {len(self.conflicts) - 10} more")
    
    # =========================================================================
    # REPLICATE & SAVE
    # =========================================================================
    
    def _save_model_week(self):
        """Save the model week (Week 0) to ModelWeekShift table."""
        from .models import ModelWeekShift
        
        print(f"\nSaving model week (Week 0)...")
        
        # Clear existing model week for this semester
        deleted, _ = ModelWeekShift.objects.filter(semester=self.semester).delete()
        if deleted:
            print(f"  Cleared {deleted} existing model week shifts")
        
        # Create ModelWeekShift objects
        model_week_objects = [
            ModelWeekShift(
                semester=self.semester,
                user_id=s['user_id'],
                day_of_week=s['day_of_week'],
                start_time=s['start_time'],
                end_time=s['end_time'],
                shift_type=s['shift_type'],
                location=s.get('location'),
                location_group=s.get('location_group'),
                team_category=s.get('team_category') or ''
            )
            for s in self.weekly_shifts
        ]
        
        ModelWeekShift.objects.bulk_create(model_week_objects, batch_size=500)
        print(f"  Saved {len(model_week_objects)} model week shifts")
        
        return len(model_week_objects)
    
    def _replicate_to_semester(self):
        """Copy model week across all weeks in semester."""
        print(f"\nReplicating across semester...")
        
        all_shifts = []
        
        # Find first Monday
        current = self.semester.start_date
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
                
                if shift_date < self.semester.start_date:
                    continue
                if shift_date > self.semester.end_date:
                    continue
                if shift_date.isoformat() in holidays:
                    continue
                
                day_of_week = shift_date.weekday()
                
                for template in self.weekly_shifts:
                    if template['day_of_week'] == day_of_week:
                        all_shifts.append({**template, 'date': shift_date})
            
            current += timedelta(days=7)
        
        print(f"  {len(all_shifts)} total shifts across {weeks} weeks")
        return all_shifts
    
    def _save_to_database(self, all_shifts):
        """Bulk create all shifts."""
        print(f"\nSaving to database...")
        
        shift_objects = [
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
        
        Shift.objects.bulk_create(shift_objects, batch_size=500)
        print(f"  Saved {len(shift_objects)} shifts")
        
        return len(shift_objects)
    
    def _error_result(self, message):
        """Return error result dict."""
        return {
            'success': False,
            'shifts_created': 0,
            'weekly_shifts': 0,
            'conflicts': [{'type': 'error', 'day': 'N/A', 'time': 'N/A', 'location': message}],
            'message': message
        }
