"""
Recurring Weekly Auto-Scheduler for The Hatchery - FIXED
=========================================================

Creates ONE model week schedule that repeats throughout the semester.

Priority Order:
1. Open Hours Hosting (highest priority) 
2. Training Hours (team-specific, limited by machine count)
3. Floater Shifts (lowest priority)

MACHINE-AWARE TRAINING LIMITS:
- Pulls actual machine counts from the database by machine_name (type)
- At least 70% of machines must remain available for users
- Maximum 30% of machines can be used for trainings per hour
- Example: 10 Prusa printers → max 3 trainers per hour
- Example: 1 Stratasys → max 1 trainer per hour (can't have 0.3 trainers!)

FIXES:
- Prevents double-booking: same person cannot be in two places at same time
- Removes aggressive hour-filling that created too many shifts
- Properly distributes hours across ALL days of the week
- Clear logging for debugging
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
    """Creates a recurring weekly schedule - FIXED VERSION with machine-aware limits"""
    
    DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # Training capacity: max 30% of machines can be used for training per hour
    TRAINING_CAPACITY_PERCENT = 0.30
    
    def __init__(self, semester):
        self.semester = semester
        self.team_members = []
        self.unavailability_map = {}  # {user_id: [(day, start, end), ...]}
        self.machine_counts = {}  # Category-level counts (legacy)
        self.machine_type_counts = {}  # {machine_name: count} - actual machine counts
        self.machine_type_to_category = {}  # {machine_name: category}
        self.category_machine_types = {}  # {category: [machine_names]}
        self.max_trainers_per_type = {}  # {machine_name: max_trainers_per_hour}
        self.weekly_shifts = []  # Shifts for the model week
        self.hours_used = {}  # Track hours used in model week
        self.training_slot_usage = {}  # {(day, start_time, machine_type): count}
        self.conflicts = []
        
    def run(self):
        """Main entry point"""
        print(f"\n{'='*60}")
        print(f"🚀 WEEKLY SCHEDULER for {self.semester.name}")
        print(f"{'='*60}\n")
        
        # Load data
        if not self._load_data():
            return {
                'success': False,
                'shifts_created': 0,
                'conflicts': self.conflicts,
                'message': 'Failed to load data'
            }
        
        # Clear existing shifts first
        self._clear_existing_shifts()
        
        # Schedule one model week
        # STRATEGY: 
        # 1. Schedule ALL required shifts (open hours + floaters) for ALL days first
        # 2. Then distribute training EVENLY across all days, cycling through days
        #    to ensure everyone gets hours spread throughout the week
        print("📅 Building Model Week:\n")
        
        # Phase 1: Schedule ALL open hours and floaters first (across all days)
        print("   Phase 1: Scheduling required shifts (open hours + floaters)...\n")
        for day in range(7):  # 0=Mon, 6=Sun
            day_name = self.DAY_NAMES[day]
            self._schedule_required_shifts(day, day_name)
        
        # Phase 2: Fill remaining hours with training - DISTRIBUTED EVENLY
        print("\n   Phase 2: Distributing training across all days...\n")
        total_training = self._distribute_training_evenly()
        print(f"\n   Total training shifts scheduled: {total_training}")
        
        # Print summary
        self._print_model_week_summary()
        
        # Validate for double-bookings
        self._validate_no_double_bookings()
        
        # Replicate across semester
        all_shifts = self._replicate_to_semester()
        
        # Save
        saved_count = self._save_to_database(all_shifts)
        
        return {
            'success': len(self.conflicts) == 0,
            'shifts_created': saved_count,
            'conflicts': self.conflicts,
            'message': self._summary_message(len(self.weekly_shifts), saved_count)
        }
    
    def _load_data(self):
        """Load all necessary data"""
        print("📊 Loading data...")
        
        # Team members (only active ones)
        self.team_members = list(
            TeamMemberProfile.objects.select_related('user')
            .filter(is_active=True)
        )
        
        if not self.team_members:
            self.conflicts.append({
                'type': 'no_team_members',
                'day': None,
                'time': None,
                'location': None
            })
            print("   ❌ No active team members found!")
            return False
        
        print(f"   ✓ {len(self.team_members)} active team members")
        
        # Initialize hours tracking
        self.hours_used = {tm.user_id: 0.0 for tm in self.team_members}
        
        # Unavailabilities - stored as list of (day, start, end) tuples per user
        unavailabilities = Unavailability.objects.filter(semester=self.semester)
        self.unavailability_map = defaultdict(list)
        for unav in unavailabilities:
            self.unavailability_map[unav.user_id].append(
                (unav.day_of_week, unav.start_time, unav.end_time)
            )
        print(f"   ✓ Loaded unavailability data")
        
        # Load machine counts from database (for training slot limits)
        self._load_machine_counts()
        
        print()
        return True
    
    def _load_machine_counts(self):
        """
        Load machine counts from the database.
        
        Tracks:
        - machine_type_counts: {machine_name: count} e.g., {'Ultimaker S5': 5, 'Prusa MK3S+': 8}
        - machine_type_to_category: {machine_name: category}
        - category_machine_types: {category: [machine_names]}
        - max_trainers_per_type: {machine_name: max_trainers} based on 30% rule
        - machine_counts: {category: total_count} (legacy, for backwards compatibility)
        """
        try:
            from machines.models import Machine
            
            # Get all machines, excluding those under maintenance if field exists
            machines_qs = Machine.objects.all()
            
            # Try to filter by maintenance status if field exists
            try:
                machines_qs = machines_qs.exclude(status='maintenance')
            except:
                pass  # Field doesn't exist, use all machines
            
            # Count by machine_name (machine type)
            type_counts = machines_qs.values('machine_name', 'category').annotate(
                count=Count('id')
            )
            
            self.machine_type_counts = {}
            self.machine_type_to_category = {}
            self.category_machine_types = defaultdict(list)
            self.max_trainers_per_type = {}
            
            print(f"\n   📦 Machine inventory (for training limits):")
            print(f"   {'─'*50}")
            
            for item in type_counts:
                machine_type = item['machine_name']
                category = item['category']
                count = item['count']
                
                if not machine_type:
                    continue
                
                self.machine_type_counts[machine_type] = count
                self.machine_type_to_category[machine_type] = category
                self.category_machine_types[category].append(machine_type)
                
                # Calculate max trainers: 30% of machines, minimum 1, rounded down
                # If only 1-3 machines, allow 1 trainer
                # If 4-6 machines, allow 1 trainer (30% of 4 = 1.2)
                # If 7-9 machines, allow 2 trainers
                # If 10+ machines, allow 3+ trainers
                max_trainers = max(1, math.floor(count * self.TRAINING_CAPACITY_PERCENT))
                self.max_trainers_per_type[machine_type] = max_trainers
                
                available_for_users = count - max_trainers
                pct_available = (available_for_users / count) * 100 if count > 0 else 0
                
                print(f"      {machine_type}: {count} machines → max {max_trainers} trainer(s)/hour ({pct_available:.0f}% for users)")
            
            # Build legacy category counts
            self.machine_counts = {}
            for category, types in self.category_machine_types.items():
                self.machine_counts[category] = sum(self.machine_type_counts.get(t, 0) for t in types)
            
            print(f"   {'─'*50}")
            print(f"   Category totals: {self.machine_counts}")
            
            # Add categories from team members that don't have machines yet
            trainer_teams = set(tm.team for tm in self.team_members if tm.is_trainer and tm.team)
            
            def normalize_category(cat):
                if not cat:
                    return ''
                return cat.lower().replace(' ', '_').replace('-', '_')
            
            normalized_machine_cats = set(normalize_category(c) for c in self.machine_counts.keys())
            
            for team in trainer_teams:
                norm_team = normalize_category(team)
                if norm_team not in normalized_machine_cats:
                    # Add this category with default of 2 training slots
                    self.machine_counts[team] = 2
                    # Add a pseudo machine type for this category
                    pseudo_type = f"{team}_generic"
                    self.machine_type_counts[pseudo_type] = 2
                    self.machine_type_to_category[pseudo_type] = team
                    self.category_machine_types[team].append(pseudo_type)
                    self.max_trainers_per_type[pseudo_type] = 1
                    print(f"   + Added category '{team}' with default 2 slots (no machines in DB)")
            
            if not self.machine_counts:
                print(f"   ⚠️ No training categories - training will be skipped")
                
        except Exception as e:
            import traceback
            print(f"   ⚠️ Could not load machines: {e}")
            traceback.print_exc()
            self.machine_counts = {}
            self.machine_type_counts = {}
            self.max_trainers_per_type = {}
    
    def _clear_existing_shifts(self):
        """Clear existing shifts for this semester"""
        deleted, _ = Shift.objects.filter(
            semester=self.semester,
            status='scheduled'
        ).delete()
        
        if deleted:
            print(f"🗑️ Cleared {deleted} existing shifts\n")
    
    def _schedule_required_shifts(self, day_of_week, day_name):
        """Schedule only open hours and floaters for a day (required shifts)"""
        
        # Get operating hours for this day
        try:
            op_hours = DailyOperatingHours.objects.get(
                semester=self.semester,
                day_of_week=day_of_week
            )
        except DailyOperatingHours.DoesNotExist:
            print(f"   {day_name}: No operating hours defined")
            return
        
        if op_hours.is_closed:
            print(f"   {day_name}: CLOSED")
            return
        
        # Schedule Open Hours
        open_count = self._schedule_open_hours(day_of_week, op_hours)
        
        # Schedule Floaters
        floater_count = self._schedule_floaters(day_of_week)
        
        print(f"   {day_name}: {open_count} open hours, {floater_count} floaters")
        
        # Show conflicts if any for this day
        day_conflicts = [c for c in self.conflicts if c.get('day') == day_name]
        if day_conflicts:
            print(f"      ⚠️ GAPS: {len(day_conflicts)}")
            for c in day_conflicts[:3]:
                print(f"         - {c['time']} @ {c['location']}")
    
    def _schedule_training_for_day(self, day_of_week, day_name):
        """DEPRECATED - use _distribute_training_evenly instead"""
        pass
    
    def _distribute_training_evenly(self):
        """
        Distribute training shifts evenly across ALL days and ALL time slots.
        
        Strategy:
        - 60% of training in MORNING hours (9am-12pm, before open hours)
        - 40% of training during rest of day
        - SPREAD EVENLY across time slots (not piling into 9am)
        - RESPECT MACHINE LIMITS: Max 30% of machines per type can be used for training
        - Max out everyone's hours within machine constraints
        """
        total_shifts = 0
        
        # Build list of all training slots for the week
        morning_slots = []  # Before open hours start
        afternoon_slots = []  # During/after open hours
        
        for day in range(7):
            try:
                op_hours = DailyOperatingHours.objects.get(
                    semester=self.semester,
                    day_of_week=day
                )
            except DailyOperatingHours.DoesNotExist:
                continue
            
            if op_hours.is_closed:
                continue
            
            if op_hours.training_disabled or not op_hours.training_start or not op_hours.training_end:
                continue
            
            slots = self._generate_hourly_slots(op_hours.training_start, op_hours.training_end)
            open_start = op_hours.open_hours_start
            
            for start, end in slots:
                if open_start and start < open_start:
                    morning_slots.append((day, start, end))
                else:
                    afternoon_slots.append((day, start, end))
        
        print(f"   Morning training slots (9am-12pm): {len(morning_slots)}")
        print(f"   Afternoon/evening training slots: {len(afternoon_slots)}")
        
        # Track counts
        training_by_day = {d: 0 for d in range(7)}
        morning_count = 0
        afternoon_count = 0
        
        # Track slot usage for even distribution across TIME SLOTS
        slot_usage = {}
        for day, start, end in morning_slots + afternoon_slots:
            slot_usage[(day, start)] = 0
        
        # Track training slot usage by category/machine type
        # Key: (day, start_time, category) -> count of trainers scheduled
        self.training_slot_usage = defaultdict(int)
        
        # Calculate total training needed
        total_training_hours_needed = 0
        trainer_categories = defaultdict(list)  # {category: [team_members]}
        
        for tm in self.team_members:
            if tm.is_trainer and tm.team:
                expected = tm.get_expected_hours(self.semester)
                used = self.hours_used.get(tm.user_id, 0)
                remaining = expected - used
                if remaining > 0:
                    total_training_hours_needed += remaining
                    trainer_categories[tm.team].append(tm)
        
        print(f"   Total training hours to fill: {total_training_hours_needed}")
        target_morning = int(total_training_hours_needed * 0.6)
        print(f"   Target distribution: {target_morning} morning (60%), {total_training_hours_needed - target_morning} afternoon (40%)")
        
        # Show trainer distribution by category
        print(f"\n   Trainers by category:")
        for cat, trainers in trainer_categories.items():
            max_per_slot = self._get_max_trainers_for_category(cat)
            print(f"      {cat}: {len(trainers)} trainers, max {max_per_slot}/hour (based on machine count)")
        
        def get_trainers_in_slot(day, start_time, category):
            """Count how many trainers of this category are already scheduled in this slot."""
            return self.training_slot_usage[(day, start_time, category)]
        
        def can_add_trainer_to_slot(day, start_time, category):
            """Check if we can add another trainer for this category in this slot."""
            current_count = get_trainers_in_slot(day, start_time, category)
            max_allowed = self._get_max_trainers_for_category(category)
            return current_count < max_allowed
        
        def find_best_slot(slots_list, tm):
            """Find the LEAST USED slot that this person can work AND has machine capacity."""
            category = tm.team
            
            person_shifts_by_day = {d: 0 for d in range(7)}
            for shift in self.weekly_shifts:
                if shift['user_id'] == tm.user_id:
                    person_shifts_by_day[shift['day_of_week']] += 1
            
            candidates = []
            for day, start, end in slots_list:
                # Check personal availability
                if not self._is_available(tm.user_id, day, start, end):
                    continue
                
                # Check if person has hours remaining
                duration = self._duration_hours(start, end)
                if self.hours_used.get(tm.user_id, 0) + duration > tm.get_expected_hours(self.semester):
                    continue
                
                # CHECK MACHINE CAPACITY - key new constraint!
                if not can_add_trainer_to_slot(day, start, category):
                    continue
                
                usage = slot_usage.get((day, start), 0)
                day_count = person_shifts_by_day[day]
                category_usage = get_trainers_in_slot(day, start, category)
                
                # Sort priority: category slot usage, then overall slot usage, then day spread, then time
                candidates.append((day, start, end, category_usage, usage, day_count))
            
            if not candidates:
                return None
            
            # Sort by: category usage (fill evenly across category slots), overall usage, day spread, time
            candidates.sort(key=lambda x: (x[3], x[4], x[5], x[1], x[0]))
            return candidates[0][:3]
        
        def assign_shift(tm, slots_list, is_morning):
            nonlocal morning_count, afternoon_count, total_shifts
            
            result = find_best_slot(slots_list, tm)
            if not result:
                return False
            
            day, start, end = result
            duration = self._duration_hours(start, end)
            category = tm.team
            
            self.weekly_shifts.append({
                'user_id': tm.user_id,
                'day_of_week': day,
                'start_time': start,
                'end_time': end,
                'shift_type': 'training',
                'location': None,
                'location_group': None,
                'team_category': category
            })
            
            self.hours_used[tm.user_id] += duration
            training_by_day[day] += 1
            slot_usage[(day, start)] = slot_usage.get((day, start), 0) + 1
            
            # Track category-specific slot usage
            self.training_slot_usage[(day, start, category)] += 1
            
            total_shifts += 1
            
            if is_morning:
                morning_count += 1
            else:
                afternoon_count += 1
            return True
        
        # Main loop
        max_iterations = 2000
        blocked_by_machine_limit = 0
        
        for iteration in range(max_iterations):
            people = [(tm, tm.get_expected_hours(self.semester) - self.hours_used.get(tm.user_id, 0))
                      for tm in self.team_members 
                      if tm.is_trainer and tm.get_expected_hours(self.semester) - self.hours_used.get(tm.user_id, 0) >= 1]
            
            if not people:
                print("   All trainers at max hours!")
                break
            
            people.sort(key=lambda x: -x[1])  # Most remaining first
            made_progress = False
            
            for tm, remaining in people:
                total_so_far = morning_count + afternoon_count
                use_morning = (total_so_far == 0) or (morning_count / total_so_far < 0.6)
                
                if use_morning:
                    if assign_shift(tm, morning_slots, True) or assign_shift(tm, afternoon_slots, False):
                        made_progress = True
                else:
                    if assign_shift(tm, afternoon_slots, False) or assign_shift(tm, morning_slots, True):
                        made_progress = True
            
            if not made_progress:
                remaining_hrs = sum(r for _, r in people)
                if remaining_hrs > 0:
                    # Check why we couldn't make progress
                    for tm, rem in people:
                        category = tm.team
                        slots_checked = 0
                        machine_blocked = 0
                        for day, start, end in morning_slots + afternoon_slots:
                            if self._is_available(tm.user_id, day, start, end):
                                slots_checked += 1
                                if not can_add_trainer_to_slot(day, start, category):
                                    machine_blocked += 1
                        if machine_blocked > 0 and machine_blocked == slots_checked:
                            blocked_by_machine_limit += 1
                    
                    print(f"   ⚠️ {len(people)} people have {remaining_hrs:.1f} hours remaining but no slots available.")
                    if blocked_by_machine_limit > 0:
                        print(f"      ({blocked_by_machine_limit} blocked by machine capacity limits)")
                break
        
        # SECOND PASS: Try to max out remaining hours by relaxing the 60/40 constraint
        # This ensures everyone gets their full hours even if distribution isn't perfect
        print(f"\n   Second pass: Maxing out remaining hours...")
        second_pass_count = 0
        
        for _ in range(500):  # Extra iterations
            people = [(tm, tm.get_expected_hours(self.semester) - self.hours_used.get(tm.user_id, 0))
                      for tm in self.team_members 
                      if tm.is_trainer and tm.get_expected_hours(self.semester) - self.hours_used.get(tm.user_id, 0) >= 1]
            
            if not people:
                break
            
            people.sort(key=lambda x: -x[1])  # Most remaining first
            made_progress = False
            
            for tm, remaining in people:
                # Try ANY available slot (ignore 60/40 split)
                if assign_shift(tm, morning_slots, True):
                    made_progress = True
                    second_pass_count += 1
                elif assign_shift(tm, afternoon_slots, False):
                    made_progress = True
                    second_pass_count += 1
            
            if not made_progress:
                break
        
        if second_pass_count > 0:
            print(f"   ✓ Second pass added {second_pass_count} more shifts")
        
        # Final check - report anyone still under hours
        under_hours = []
        for tm in self.team_members:
            if tm.is_trainer:
                expected = tm.get_expected_hours(self.semester)
                used = self.hours_used.get(tm.user_id, 0)
                if used < expected - 0.5:  # More than 0.5 hours short
                    under_hours.append((tm, expected, used))
        
        if under_hours:
            print(f"\n   ⚠️ {len(under_hours)} trainers still under target hours:")
            for tm, expected, used in under_hours[:5]:
                print(f"      {tm.user.get_full_name()}: {used:.1f}/{expected:.1f} hrs")
            if len(under_hours) > 5:
                print(f"      ... and {len(under_hours) - 5} more")
        
        # Reports
        print(f"\n   Training distribution by day:")
        for day in range(7):
            if training_by_day[day] > 0:
                print(f"      {self.DAY_NAMES[day]}: {training_by_day[day]} training shifts")
        
        print(f"\n   Training per time slot:")
        slot_by_time = {}
        for (day, start), count in slot_usage.items():
            t = start.strftime('%H:%M')
            slot_by_time[t] = slot_by_time.get(t, 0) + count
        for t in sorted(slot_by_time.keys()):
            if slot_by_time[t] > 0:
                print(f"      {t}: {slot_by_time[t]} trainings")
        
        total_training = morning_count + afternoon_count + second_pass_count
        if total_training > 0:
            pct = (morning_count / total_training) * 100 if total_training else 0
            print(f"\n   Morning vs Afternoon: {morning_count} ({pct:.0f}%) / {afternoon_count + second_pass_count} ({100-pct:.0f}%)")
        
        return total_shifts + second_pass_count
    
    def _schedule_day(self, day_of_week, day_name):
        """DEPRECATED - kept for reference. Use _schedule_required_shifts and _schedule_training_for_day instead."""
        pass
    
    # =========================================================================
    # PRIORITY 1: OPEN HOURS
    # =========================================================================
    
    def _schedule_open_hours(self, day_of_week, op_hours):
        """Schedule open hours hosting for this day"""
        shifts_created = 0
        
        requirements = ShiftRequirement.objects.filter(
            semester=self.semester,
            day_of_week=day_of_week,
            hosts_required__gt=0
        ).select_related('location', 'location_group').order_by('time_start')
        
        # Debug: Show what requirements were found
        req_count = requirements.count()
        if req_count == 0:
            print(f"      ⚠️ No open hours requirements found for day {day_of_week}!")
            return 0
        
        # Group by time slot for logging
        time_slots = {}
        for req in requirements:
            key = f"{req.time_start.strftime('%H:%M')}-{req.time_end.strftime('%H:%M')}"
            if key not in time_slots:
                time_slots[key] = 0
            time_slots[key] += req.hosts_required
        
        print(f"      Requirements found: {time_slots}")
        
        for req in requirements:
            for host_slot in range(req.hosts_required):
                assigned = self._assign_shift(
                    day_of_week=day_of_week,
                    start_time=req.time_start,
                    end_time=req.time_end,
                    shift_type='open_hours',
                    location=req.location,
                    location_group=req.location_group
                )
                
                if assigned:
                    shifts_created += 1
                else:
                    loc_name = (req.location.name if req.location 
                               else req.location_group.name if req.location_group 
                               else "Unknown")
                    self.conflicts.append({
                        'type': 'open_hours_gap',
                        'day': self.DAY_NAMES[day_of_week],
                        'time': f"{req.time_start.strftime('%H:%M')}-{req.time_end.strftime('%H:%M')}",
                        'location': loc_name
                    })
        
        return shifts_created
    
    # =========================================================================
    # PRIORITY 2: TRAINING
    # =========================================================================
    
    def _schedule_training(self, day_of_week, op_hours):
        """Schedule training hours for this day"""
        shifts_created = 0
        
        # Generate hourly slots
        slots = self._generate_hourly_slots(op_hours.training_start, op_hours.training_end)
        
        # Create a normalized category mapping for matching
        def normalize_category(cat):
            if not cat:
                return ''
            return cat.lower().replace(' ', '_').replace('-', '_')
        
        for start_time, end_time in slots:
            # For each machine category
            for category, machine_count in self.machine_counts.items():
                norm_category = normalize_category(category)
                
                # Get trainers for this category (match normalized team names)
                category_trainers = [
                    tm for tm in self.team_members 
                    if tm.is_trainer and normalize_category(tm.team) == norm_category
                ]
                
                if not category_trainers:
                    continue
                
                # Find available trainers for this slot
                available = []
                for tm in category_trainers:
                    if self._is_available(tm.user_id, day_of_week, start_time, end_time):
                        available.append(tm)
                
                if not available:
                    continue
                
                # Sort by hours used (least first for fair distribution)
                available.sort(key=lambda tm: self.hours_used[tm.user_id])
                
                # Assign up to machine_count trainers (limited by actual availability)
                trainers_to_assign = min(len(available), machine_count)
                
                for i in range(trainers_to_assign):
                    tm = available[i]
                    
                    # Double-check availability (may have changed after previous assignment)
                    if not self._is_available(tm.user_id, day_of_week, start_time, end_time):
                        continue
                    
                    duration = self._duration_hours(start_time, end_time)
                    
                    self.weekly_shifts.append({
                        'user_id': tm.user_id,
                        'day_of_week': day_of_week,
                        'start_time': start_time,
                        'end_time': end_time,
                        'shift_type': 'training',
                        'location': None,
                        'location_group': None,
                        'team_category': category
                    })
                    
                    self.hours_used[tm.user_id] += duration
                    shifts_created += 1
        
        return shifts_created
    
    # =========================================================================
    # PRIORITY 3: FLOATERS
    # =========================================================================
    
    def _schedule_floaters(self, day_of_week):
        """Schedule floater shifts for this day"""
        shifts_created = 0
        
        requirements = ShiftRequirement.objects.filter(
            semester=self.semester,
            day_of_week=day_of_week,
            floaters_required__gt=0
        )
        
        for req in requirements:
            for floater_slot in range(req.floaters_required):
                assigned = self._assign_shift(
                    day_of_week=day_of_week,
                    start_time=req.time_start,
                    end_time=req.time_end,
                    shift_type='floater'
                )
                
                if assigned:
                    shifts_created += 1
                else:
                    self.conflicts.append({
                        'type': 'floater_gap',
                        'day': self.DAY_NAMES[day_of_week],
                        'time': f"{req.time_start.strftime('%H:%M')}-{req.time_end.strftime('%H:%M')}",
                        'location': 'General'
                    })
        
        return shifts_created
    
    # =========================================================================
    # CORE ASSIGNMENT LOGIC
    # =========================================================================
    
    def _assign_shift(self, day_of_week, start_time, end_time, shift_type,
                      location=None, location_group=None, team_category=None):
        """
        Assign the best available person to a shift.
        Returns True if assigned, False if no one available.
        
        THIS IS THE CRITICAL FUNCTION - it must prevent double-booking!
        """
        
        duration = self._duration_hours(start_time, end_time)
        
        # Find all available team members
        available = []
        for tm in self.team_members:
            if self._is_available(tm.user_id, day_of_week, start_time, end_time):
                available.append(tm)
        
        if not available:
            return False
        
        # Sort by hours used (fair distribution - least hours first)
        available.sort(key=lambda tm: self.hours_used[tm.user_id])
        
        # Assign to the person with least hours
        person = available[0]
        
        # Create the shift
        self.weekly_shifts.append({
            'user_id': person.user_id,
            'day_of_week': day_of_week,
            'start_time': start_time,
            'end_time': end_time,
            'shift_type': shift_type,
            'location': location,
            'location_group': location_group,
            'team_category': team_category
        })
        
        self.hours_used[person.user_id] += duration
        return True
    
    def _is_available(self, user_id, day_of_week, start_time, end_time):
        """
        Check if a user is available for a time slot.
        
        CRITICAL: This checks:
        1. Weekly hours limit
        2. Unavailability entries
        3. Already assigned shifts (PREVENTS DOUBLE-BOOKING!)
        """
        
        # Check 1: Weekly hours limit
        duration = self._duration_hours(start_time, end_time)
        team_member = next((tm for tm in self.team_members if tm.user_id == user_id), None)
        
        if not team_member:
            return False
        
        expected_hours = team_member.get_expected_hours(self.semester)
        if self.hours_used.get(user_id, 0) + duration > expected_hours:
            return False
        
        # Check 2: Unavailability
        for (unav_day, unav_start, unav_end) in self.unavailability_map.get(user_id, []):
            if unav_day == day_of_week:
                if self._times_overlap(start_time, end_time, unav_start, unav_end):
                    return False
        
        # Check 3: Already assigned shifts (CRITICAL - prevents double-booking)
        for shift in self.weekly_shifts:
            if shift['user_id'] == user_id and shift['day_of_week'] == day_of_week:
                if self._times_overlap(start_time, end_time, 
                                      shift['start_time'], shift['end_time']):
                    return False
        
        return True
    
    def _get_max_trainers_for_category(self, category):
        """
        Get the maximum number of trainers allowed per hour for a category.
        
        Based on the 30% rule: max 30% of machines can be used for training.
        This ensures at least 70% of machines remain available for users.
        
        Args:
            category: The team/category name (e.g., '3D Printing', 'Laser')
        
        Returns:
            int: Maximum trainers allowed per hour for this category
        """
        # Normalize category name for matching
        def normalize(cat):
            if not cat:
                return ''
            return cat.lower().replace(' ', '_').replace('-', '_')
        
        norm_category = normalize(category)
        
        # First, try to find matching machine types in this category
        total_machines = 0
        matched_types = []
        
        for machine_type, cat in self.machine_type_to_category.items():
            if normalize(cat) == norm_category:
                matched_types.append(machine_type)
                total_machines += self.machine_type_counts.get(machine_type, 0)
        
        if total_machines > 0:
            # Calculate based on total machines in category
            max_trainers = max(1, math.floor(total_machines * self.TRAINING_CAPACITY_PERCENT))
            return max_trainers
        
        # Fallback: check legacy machine_counts
        for cat, count in self.machine_counts.items():
            if normalize(cat) == norm_category:
                return max(1, math.floor(count * self.TRAINING_CAPACITY_PERCENT))
        
        # Default: allow 1 trainer if category not found
        return 1
    
    # =========================================================================
    # VALIDATION
    # =========================================================================
    
    def _validate_no_double_bookings(self):
        """Verify no one is double-booked"""
        print("\n🔍 Validating for double-bookings...")
        
        # Group shifts by user and day
        user_day_shifts = defaultdict(list)
        for shift in self.weekly_shifts:
            key = (shift['user_id'], shift['day_of_week'])
            user_day_shifts[key].append(shift)
        
        double_bookings = 0
        for (user_id, day), shifts in user_day_shifts.items():
            # Check each pair
            for i, s1 in enumerate(shifts):
                for s2 in shifts[i+1:]:
                    if self._times_overlap(s1['start_time'], s1['end_time'],
                                          s2['start_time'], s2['end_time']):
                        double_bookings += 1
                        user = next((tm for tm in self.team_members if tm.user_id == user_id), None)
                        user_name = user.user.get_full_name() if user else f"User {user_id}"
                        
                        print(f"   ❌ DOUBLE-BOOKING: {user_name} on {self.DAY_NAMES[day]}")
                        print(f"      Shift 1: {s1['shift_type']} {s1['start_time']}-{s1['end_time']}")
                        print(f"      Shift 2: {s2['shift_type']} {s2['start_time']}-{s2['end_time']}")
                        
                        self.conflicts.append({
                            'type': 'double_booking',
                            'day': self.DAY_NAMES[day],
                            'time': f"{s1['start_time']}-{s1['end_time']} vs {s2['start_time']}-{s2['end_time']}",
                            'location': user_name
                        })
        
        if double_bookings == 0:
            print("   ✓ No double-bookings found")
        else:
            print(f"   ❌ Found {double_bookings} double-bookings!")
    
    def _print_model_week_summary(self):
        """Print summary of model week"""
        print(f"\n📊 Model Week Summary:")
        print(f"   Total shifts: {len(self.weekly_shifts)}")
        
        # Count by type
        type_counts = defaultdict(int)
        for shift in self.weekly_shifts:
            type_counts[shift['shift_type']] += 1
        
        for shift_type, count in sorted(type_counts.items()):
            print(f"   {shift_type}: {count}")
        
        # Hours per person
        print(f"\n   Hours per person:")
        for tm in sorted(self.team_members, key=lambda t: self.hours_used.get(t.user_id, 0), reverse=True):
            used = self.hours_used.get(tm.user_id, 0)
            expected = tm.get_expected_hours(self.semester)
            if used > 0:
                status = "✓" if used <= expected else "⚠️ OVER"
                print(f"      {tm.user.get_full_name()[:25]:25} {used:5.1f} / {expected:5.1f} hrs {status}")
        
        # Machine capacity usage report
        if self.training_slot_usage:
            print(f"\n   🔧 Machine Capacity Usage (Training):")
            
            # Group by category
            category_max_usage = defaultdict(int)
            category_slot_count = defaultdict(int)
            
            for (day, start_time, category), count in self.training_slot_usage.items():
                max_allowed = self._get_max_trainers_for_category(category)
                category_max_usage[category] = max(category_max_usage[category], count)
                category_slot_count[category] += 1
            
            for category in sorted(category_max_usage.keys()):
                max_used = category_max_usage[category]
                max_allowed = self._get_max_trainers_for_category(category)
                total_machines = self.machine_counts.get(category, 0)
                slots_used = category_slot_count[category]
                
                status = "✓" if max_used <= max_allowed else "⚠️ OVER"
                print(f"      {category:20} Peak: {max_used}/{max_allowed} trainers/hr ({total_machines} machines) {status}")
    
    # =========================================================================
    # REPLICATION
    # =========================================================================
    
    def _replicate_to_semester(self):
        """Replicate the model week across all semester weeks"""
        print(f"\n🔄 Replicating across semester...")
        
        all_shifts = []
        current = self.semester.start_date
        
        # Find first Monday
        while current.weekday() != 0:
            current += timedelta(days=1)
        
        week_count = 0
        while current <= self.semester.end_date:
            week_count += 1
            
            # For each day in this week
            for day_offset in range(7):
                shift_date = current + timedelta(days=day_offset)
                
                if shift_date < self.semester.start_date:
                    continue
                if shift_date > self.semester.end_date:
                    continue
                
                # Skip holidays
                if shift_date.isoformat() in (self.semester.holidays or []):
                    continue
                
                day_of_week = shift_date.weekday()
                
                # Copy shifts for this day
                for shift_template in self.weekly_shifts:
                    if shift_template['day_of_week'] == day_of_week:
                        all_shifts.append({
                            **shift_template,
                            'date': shift_date
                        })
            
            current += timedelta(days=7)
        
        print(f"   ✓ Created {len(all_shifts)} shifts across {week_count} weeks")
        return all_shifts
    
    def _save_to_database(self, all_shifts):
        """Save shifts to database using bulk_create for efficiency"""
        print(f"\n💾 Saving to database...")
        
        shifts_to_create = []
        for shift_data in all_shifts:
            shift = Shift(
                semester=self.semester,
                user_id=shift_data['user_id'],
                date=shift_data['date'],
                start_time=shift_data['start_time'],
                end_time=shift_data['end_time'],
                shift_type=shift_data['shift_type'],
                location=shift_data.get('location'),
                location_group=shift_data.get('location_group'),
                team_category=shift_data.get('team_category') or '',
                status='scheduled'
            )
            shifts_to_create.append(shift)
        
        # Bulk create for efficiency
        Shift.objects.bulk_create(shifts_to_create, batch_size=500)
        
        print(f"   ✓ Saved {len(shifts_to_create)} shifts")
        return len(shifts_to_create)
    
    def _summary_message(self, weekly_shifts, total_shifts):
        """Generate summary message"""
        lines = [
            f"Scheduling complete!",
            f"",
            f"Model week: {weekly_shifts} shifts",
            f"Total semester: {total_shifts} shifts",
        ]
        
        if self.conflicts:
            lines.append(f"")
            lines.append(f"⚠️ {len(self.conflicts)} issues found:")
            for c in self.conflicts[:5]:
                lines.append(f"  • {c['type']}: {c.get('day', '')} {c.get('time', '')} @ {c.get('location', '')}")
            if len(self.conflicts) > 5:
                lines.append(f"  ... and {len(self.conflicts) - 5} more")
        
        return "\n".join(lines)
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _times_overlap(self, start1, end1, start2, end2):
        """Check if two time ranges overlap"""
        return not (end1 <= start2 or start1 >= end2)
    
    def _duration_hours(self, start_time, end_time):
        """Calculate duration in hours"""
        start = datetime.combine(dt_date.today(), start_time)
        end = datetime.combine(dt_date.today(), end_time)
        return (end - start).total_seconds() / 3600
    
    def _generate_hourly_slots(self, start_time, end_time):
        """Generate 1-hour time slots"""
        slots = []
        current_hour = start_time.hour
        end_hour = end_time.hour
        
        while current_hour < end_hour:
            slot_start = time(hour=current_hour, minute=0)
            slot_end = time(hour=current_hour + 1, minute=0)
            slots.append((slot_start, slot_end))
            current_hour += 1
        
        return slots