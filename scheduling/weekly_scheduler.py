"""
Recurring Weekly Auto-Scheduler for The Hatchery
=================================================

Creates ONE model week schedule that repeats throughout the semester.

Priority Order:
1. Open Hours Hosting (highest priority) 
2. Training Hours (team-specific, limited by machine count)
3. Floater Shifts (lowest priority)

Key Constraints:
- Each person has a weekly hour limit
- No overlaps between shift types for same person (open hours != training)
- Training can overlap with floater for same person
- Stay within weekly hour budgets
"""

from datetime import datetime, timedelta, time, date as dt_date
from collections import defaultdict
from django.db.models import Count

from .models import (
    Semester, DailyOperatingHours, ShiftRequirement, 
    TeamMemberProfile, Unavailability, Shift
)
from machines.models import Machine


class WeeklyScheduler:
    """Creates a recurring weekly schedule"""
    
    def __init__(self, semester):
        self.semester = semester
        self.team_members = []
        self.unavailability_map = {}
        self.machine_counts = {}
        self.weekly_shifts = []  # Shifts for the model week
        self.hours_used = {}  # Track hours used in model week
        self.conflicts = []
        
    def run(self):
        """Main entry point"""
        print(f"🚀 Creating recurring weekly schedule for {self.semester.name}\n")
        
        # Load data
        self._load_data()
        
        # Schedule one model week
        for day in range(7):  # 0=Mon, 6=Sun
            day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][day]
            print(f"📅 Scheduling {day_name}...")
            
            self._schedule_day(day)
        
        # Validate
        self._check_weekly_hours()
        
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
        
        # Team members
        self.team_members = list(TeamMemberProfile.objects.select_related('user').all())
        print(f"   {len(self.team_members)} team members")
        
        # Initialize hours tracking
        self.hours_used = {tm.user_id: 0.0 for tm in self.team_members}
        
        # Unavailabilities
        unavailabilities = Unavailability.objects.filter(semester=self.semester)
        self.unavailability_map = defaultdict(list)
        for unav in unavailabilities:
            self.unavailability_map[unav.user_id].append(unav)
        
        # Machine counts
        machine_counts = Machine.objects.values('category').annotate(count=Count('id'))
        self.machine_counts = {item['category']: item['count'] for item in machine_counts}
        print(f"   Machine counts: {self.machine_counts}\n")
    
    def _schedule_day(self, day_of_week):
        """Schedule all shifts for one day of the week"""
        
        # Get operating hours for this day
        try:
            op_hours = DailyOperatingHours.objects.get(
                semester=self.semester,
                day_of_week=day_of_week
            )
        except DailyOperatingHours.DoesNotExist:
            print(f"   ⚠️  No operating hours defined")
            return
        
        if op_hours.is_closed:
            print(f"   🚫 Closed")
            return
        
        # Priority 1: Open Hours
        self._schedule_open_hours(day_of_week, op_hours)
        
        # Priority 2: Training
        self._schedule_training(day_of_week, op_hours)
        
        # Priority 3: Floaters
        self._schedule_floaters(day_of_week, op_hours)
        
        # Priority 4: Fill remaining hours with backup coverage
        self._fill_remaining_hours(day_of_week, op_hours)
    
    def _schedule_open_hours(self, day_of_week, op_hours):
        """Schedule open hours hosting for this day"""
        
        requirements = ShiftRequirement.objects.filter(
            semester=self.semester,
            day_of_week=day_of_week,
            hosts_required__gt=0
        )
        
        for req in requirements:
            for host_slot in range(req.hosts_required):
                # Try to fill this slot
                assigned = self._assign_open_hours_shift(
                    day_of_week, 
                    req.time_start, 
                    req.time_end,
                    req.location,
                    req.location_group
                )
                
                if not assigned:
                    self.conflicts.append({
                        'type': 'open_hours_gap',
                        'day': day_of_week,
                        'time': f"{req.time_start}-{req.time_end}",
                        'location': req.location or req.location_group
                    })
    
    def _assign_open_hours_shift(self, day_of_week, start_time, end_time, location, location_group):
        """Try to assign one open hours shift"""
        
        # Find available people
        available = []
        for tm in self.team_members:
            if self._can_work_open_hours(tm, day_of_week, start_time, end_time):
                available.append(tm)
        
        if not available:
            return False
        
        # Pick person with fewest hours
        available.sort(key=lambda tm: self.hours_used[tm.user_id])
        person = available[0]
        
        # Create shift
        duration = self._duration_hours(start_time, end_time)
        self.weekly_shifts.append({
            'user_id': person.user_id,
            'day_of_week': day_of_week,
            'start_time': start_time,
            'end_time': end_time,
            'shift_type': 'open_hours',
            'location': location,
            'location_group': location_group,
            'team_category': None
        })
        
        self.hours_used[person.user_id] += duration
        return True
    
    def _can_work_open_hours(self, team_member, day_of_week, start_time, end_time):
        """Check if someone can work open hours at this time"""
        
        # Check weekly hours limit
        duration = self._duration_hours(start_time, end_time)
        expected_hours = team_member.get_expected_hours(self.semester)
        if self.hours_used[team_member.user_id] + duration > expected_hours:
            return False
        
        # Check unavailability
        for unav in self.unavailability_map.get(team_member.user_id, []):
            if unav.day_of_week == day_of_week:
                if self._times_overlap(start_time, end_time, unav.start_time, unav.end_time):
                    return False
        
        # Check for conflicts with already assigned shifts
        for shift in self.weekly_shifts:
            if shift['user_id'] == team_member.user_id and shift['day_of_week'] == day_of_week:
                if self._times_overlap(start_time, end_time, shift['start_time'], shift['end_time']):
                    return False
        
        return True
    
    def _schedule_training(self, day_of_week, op_hours):
        """Schedule training hours for this day"""
        
        # Generate hourly slots during training hours
        slots = self._generate_hourly_slots(op_hours.training_start, op_hours.training_end)
        
        for start_time, end_time in slots:
            # For each machine category
            for category, machine_count in self.machine_counts.items():
                # Get team members for this category
                category_members = [tm for tm in self.team_members if tm.team == category]
                
                if not category_members:
                    continue
                
                # Find available members
                available = []
                for tm in category_members:
                    if self._can_work_training(tm, day_of_week, start_time, end_time):
                        available.append(tm)
                
                # Assign up to machine_count trainers
                available.sort(key=lambda tm: self.hours_used[tm.user_id])
                trainers_to_assign = min(len(available), machine_count)
                
                for i in range(trainers_to_assign):
                    tm = available[i]
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
    
    def _can_work_training(self, team_member, day_of_week, start_time, end_time):
        """Check if someone can work training at this time"""
        
        # Check weekly hours
        duration = self._duration_hours(start_time, end_time)
        expected_hours = team_member.get_expected_hours(self.semester)
        if self.hours_used[team_member.user_id] + duration > expected_hours:
            return False
        
        # Check unavailability
        for unav in self.unavailability_map.get(team_member.user_id, []):
            if unav.day_of_week == day_of_week:
                if self._times_overlap(start_time, end_time, unav.start_time, unav.end_time):
                    return False
        
        # Check for conflicts with OPEN HOURS shifts (training can overlap with floater)
        for shift in self.weekly_shifts:
            if shift['user_id'] == team_member.user_id and shift['day_of_week'] == day_of_week:
                if shift['shift_type'] == 'open_hours':  # Only block if open hours
                    if self._times_overlap(start_time, end_time, shift['start_time'], shift['end_time']):
                        return False
        
        return True
    
    def _schedule_floaters(self, day_of_week, op_hours):
        """Schedule floater shifts for this day"""
        
        requirements = ShiftRequirement.objects.filter(
            semester=self.semester,
            day_of_week=day_of_week,
            floaters_required__gt=0
        )
        
        for req in requirements:
            for floater_slot in range(req.floaters_required):
                self._assign_floater_shift(day_of_week, req.time_start, req.time_end)
    
    def _assign_floater_shift(self, day_of_week, start_time, end_time):
        """Try to assign one floater shift"""
        
        # Find available people
        available = []
        for tm in self.team_members:
            if self._can_work_floater(tm, day_of_week, start_time, end_time):
                available.append(tm)
        
        if not available:
            return False
        
        # Pick person with fewest hours
        available.sort(key=lambda tm: self.hours_used[tm.user_id])
        person = available[0]
        
        # Create shift
        duration = self._duration_hours(start_time, end_time)
        self.weekly_shifts.append({
            'user_id': person.user_id,
            'day_of_week': day_of_week,
            'start_time': start_time,
            'end_time': end_time,
            'shift_type': 'floater',
            'location': None,
            'location_group': None,
            'team_category': None
        })
        
        self.hours_used[person.user_id] += duration
        return True
    
    def _can_work_floater(self, team_member, day_of_week, start_time, end_time):
        """Check if someone can work as floater - floaters can overlap with training"""
        
        # Check weekly hours
        duration = self._duration_hours(start_time, end_time)
        expected_hours = team_member.get_expected_hours(self.semester)
        if self.hours_used[team_member.user_id] + duration > expected_hours:
            return False
        
        # Check unavailability
        for unav in self.unavailability_map.get(team_member.user_id, []):
            if unav.day_of_week == day_of_week:
                if self._times_overlap(start_time, end_time, unav.start_time, unav.end_time):
                    return False
        
        # Check for conflicts with OPEN HOURS only (floater can overlap with training)
        for shift in self.weekly_shifts:
            if shift['user_id'] == team_member.user_id and shift['day_of_week'] == day_of_week:
                if shift['shift_type'] == 'open_hours':
                    if self._times_overlap(start_time, end_time, shift['start_time'], shift['end_time']):
                        return False
        
        return True
    
    def _fill_remaining_hours(self, day_of_week, op_hours):
        """
        Priority 4: Fill remaining hours with backup trainers and extra floaters.
        This provides extra coverage and uses all available team member capacity.
        """
        
        # Find people with remaining hours
        people_with_capacity = []
        for tm in self.team_members:
            expected = tm.get_expected_hours(self.semester)
            used = self.hours_used.get(tm.user_id, 0)
            remaining = expected - used
            
            if remaining >= 1.0:  # At least 1 hour remaining
                people_with_capacity.append({
                    'member': tm,
                    'remaining_hours': remaining
                })
        
        if not people_with_capacity:
            return  # Everyone is at capacity
        
        # Sort by most remaining hours first
        people_with_capacity.sort(key=lambda x: x['remaining_hours'], reverse=True)
        
        # Generate time slots for backup coverage
        # Use training hours as the window (when the space is most active)
        if not op_hours.training_start or not op_hours.training_end:
            return
        
        slots = self._generate_hourly_slots(op_hours.training_start, op_hours.training_end)
        
        for person_data in people_with_capacity:
            tm = person_data['member']
            
            # Try to assign backup shifts until they reach their capacity
            for start_time, end_time in slots:
                if self.hours_used[tm.user_id] >= tm.get_expected_hours(self.semester):
                    break  # This person is now at capacity
                
                # Decide what type of backup shift to assign
                if tm.team:  # Has a team - make them backup trainer
                    if self._can_work_training(tm, day_of_week, start_time, end_time):
                        # Assign as backup trainer
                        duration = self._duration_hours(start_time, end_time)
                        
                        self.weekly_shifts.append({
                            'user_id': tm.user_id,
                            'day_of_week': day_of_week,
                            'start_time': start_time,
                            'end_time': end_time,
                            'shift_type': 'training',
                            'location': None,
                            'location_group': None,
                            'team_category': tm.team
                        })
                        
                        self.hours_used[tm.user_id] += duration
                
                else:  # No team - make them extra floater
                    if self._can_work_floater(tm, day_of_week, start_time, end_time):
                        # Assign as extra floater
                        duration = self._duration_hours(start_time, end_time)
                        
                        self.weekly_shifts.append({
                            'user_id': tm.user_id,
                            'day_of_week': day_of_week,
                            'start_time': start_time,
                            'end_time': end_time,
                            'shift_type': 'floater',
                            'location': None,
                            'location_group': None,
                            'team_category': None
                        })
                        
                        self.hours_used[tm.user_id] += duration
    
    def _check_weekly_hours(self):
        """Validate weekly hours for all team members"""
        print(f"\n📊 Weekly hours per person:")
        for tm in self.team_members:
            expected = tm.get_expected_hours(self.semester)
            actual = self.hours_used.get(tm.user_id, 0)
            status = "✅" if actual <= expected else "⚠️"
            print(f"   {status} {tm.user.email:30} {actual:.1f}/{expected:.1f} hrs")
    
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
                
                if shift_date > self.semester.end_date:
                    break
                
                # Skip holidays
                if shift_date.isoformat() in self.semester.holidays:
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
        
        print(f"   Created {len(all_shifts)} shifts across {week_count} weeks")
        return all_shifts
    
    def _save_to_database(self, all_shifts):
        """Save shifts to database"""
        print(f"\n💾 Saving to database...")
        
        created = 0
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
                team_category=shift_data.get('team_category'),
                status='scheduled'
            )
            shift.save()
            created += 1
        
        print(f"   ✅ Saved {created} shifts")
        return created
    
    def _summary_message(self, weekly_shifts, total_shifts):
        """Generate summary message"""
        msg = f"\n{'='*60}\n"
        msg += f"SCHEDULING COMPLETE\n"
        msg += f"{'='*60}\n"
        msg += f"Model week: {weekly_shifts} shifts\n"
        msg += f"Total semester: {total_shifts} shifts\n"
        
        if self.conflicts:
            msg += f"\n⚠️  WARNING: {len(self.conflicts)} coverage gaps found!\n"
            msg += f"\nAction required:\n"
            msg += f"  • Review uncovered shifts\n"
            msg += f"  • Increase team member hours\n"
            msg += f"  • Add more team members\n"
            msg += f"  • Adjust requirements\n"
        
        return msg
    
    # Helper methods
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