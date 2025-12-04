from scheduling.models import Shift, Semester
from datetime import date, timedelta

semester_id = 1  # Your active semester

# Test what the API would return
shifts = Shift.objects.filter(semester_id=semester_id).select_related('user', 'location', 'location_group')

print(f"Total shifts found: {shifts.count()}")
print(f"First 3 shifts:")
for s in shifts[:3]:
    print(f"  ID: {s.id}, Date: {s.date}, User: {s.user.email}, Type: {s.shift_type}")

# Check what the API builds
data = []
for shift in shifts[:5]:
    data.append({
        'id': shift.id,
        'date': shift.date.isoformat(),
        'start': shift.start_time.strftime('%H:%M'),
        'end': shift.end_time.strftime('%H:%M'),
        'user': shift.user.get_full_name() or shift.user.email,
        'user_id': shift.user.id,
        'shift_type': shift.shift_type,
    })

print(f"\nAPI would return {len(data)} sample items:")
for d in data:
    print(f"  {d}")