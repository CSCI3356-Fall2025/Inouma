print(">>> Importing modules...")
from scheduling.models import Semester, Shift
from scheduling.weekly_scheduler import WeeklyScheduler
from collections import defaultdict
from datetime import timedelta
print(">>> Imports complete.\n")

print(">>> Clearing old shifts...")
Shift.objects.all().delete()
print("✔ Old shifts cleared.\n")

print(">>> Fetching semester (id=1)...")
semester = Semester.objects.get(id=1)
print(f"✔ Loaded semester: {semester.name}\n")

print(">>> Running WeeklyScheduler...")
scheduler = WeeklyScheduler(semester)
result = scheduler.run()
print("✔ Scheduler finished.\n")

print(">>> Scheduler message:")
print(f"    {result['message']}\n")

print(">>> Calculating weekly hour totals...")
weekly_hours = defaultdict(lambda: defaultdict(float))
for shift in Shift.objects.all():
    week_start = shift.date - timedelta(days=shift.date.weekday())
    weekly_hours[shift.user.email][week_start] += shift.duration_hours()
print("✔ Weekly hours calculated.\n")

print("="*60)
print("WEEKLY HOURS SUMMARY (First 3 weeks per person)")
print("="*60)

for email in sorted(weekly_hours.keys()):
    print(f"\n{email}:")
    weeks = weekly_hours[email]
    for week in sorted(weeks.keys())[:3]:
        print(f"  Week of {week}: {weeks[week]:.1f} hrs")

print("\n>>> Done.")
