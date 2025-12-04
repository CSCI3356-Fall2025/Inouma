# In Django shell (python manage.py shell)

from scheduling.models import Semester, Shift, DailyOperatingHours, ShiftRequirement
from django.contrib.auth import get_user_model

User = get_user_model()

print("\n" + "="*60)
print("SCHEDULING DEBUG REPORT")
print("="*60)

# 1. Check Semesters
print("\n📅 SEMESTERS:")
print("-" * 40)
for sem in Semester.objects.all().order_by('-start_date'):
    status = "✅ ACTIVE" if sem.is_active else "⬜ Inactive"
    shift_count = Shift.objects.filter(semester=sem).count()
    print(f"  {status} {sem.name} (ID: {sem.id}) - {shift_count} shifts")

# 2. Active Semester Details
print("\n📊 ACTIVE SEMESTER SHIFTS:")
print("-" * 40)
active = Semester.objects.filter(is_active=True).first()
if active:
    shifts = Shift.objects.filter(semester=active)
    print(f"  Total: {shifts.count()}")
    print(f"  Open Hours: {shifts.filter(shift_type='open_hours').count()}")
    print(f"  Training: {shifts.filter(shift_type='training').count()}")
    print(f"  Floater: {shifts.filter(shift_type='floater').count()}")
    
    # Sample shifts
    print("\n  Sample shifts:")
    for s in shifts[:5]:
        print(f"    • {s.date} {s.start_time}-{s.end_time} | {s.user.email} | {s.shift_type}")
else:
    print("  ❌ No active semester!")

# 3. Team Members
print("\n👥 TEAM MEMBERS:")
print("-" * 40)
team = User.objects.filter(role__in=['Team Member', 'Staff'], is_active=True)
print(f"  Total: {team.count()}")
print(f"  Trainers: {team.filter(is_trainer=True).count()}")

# 4. Shift Requirements
print("\n📋 SHIFT REQUIREMENTS:")
print("-" * 40)
if active:
    reqs = ShiftRequirement.objects.filter(semester=active)
    print(f"  Total: {reqs.count()}")
else:
    print("  No active semester to check")

print("\n" + "="*60)