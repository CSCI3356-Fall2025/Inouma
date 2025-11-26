import datetime as dt
from datetime import datetime, timedelta, date
import json
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.utils.dateparse import parse_date
from django.contrib.auth import get_user_model
from .models import Shift, Unavailability, ScheduleWindow
from .roles import is_admin, is_trainer
from .utils import daterange, overlaps

User = get_user_model()

@login_required
@user_passes_test(is_admin)
def list_shifts_json(request):
    items = Shift.objects.select_related("trainer").order_by("date", "start_time")
    
    week_start_str = request.GET.get("week_start")
    if week_start_str:
        week_start = parse_date(week_start_str)
        if week_start:
            week_end = week_start + timedelta(days=6)
            items = items.filter(date__gte=week_start, date__lt=week_end)

    data = [
        {
            "id": s.id,
            "date": s.date.isoformat(),
            "start": s.start_time.strftime("%H:%M"),
            "end":   s.end_time.strftime("%H:%M"),
            "trainer": str(s.trainer),
            "trainer_id": s.trainer_id,
            "team": s.team,
        } for s in items
    ]
    return JsonResponse({"shifts": data})

@login_required
@user_passes_test(is_admin)
@require_POST
def clear_shifts(request):
    Shift.objects.all().delete()
    return JsonResponse({"ok": True, "deleted": True})

@login_required
@user_passes_test(is_trainer)
@require_POST
def add_unavailability(request):
    try:
        p = json.loads(request.body.decode("utf-8"))
        weekday = int(p["weekday"])
        sh, sm = map(int, p["start"].split(":"))
        eh, em = map(int, p["end"].split(":"))
        start = dt.time(sh, sm)
        end = dt.time(eh, em)
        if end <= start:
            raise ValueError("end must be after start")
        Unavailability.objects.create(trainer=request.user, weekday=weekday, start_time=start, end_time=end)
        return JsonResponse({"ok": True})
    except Exception as e:
        return HttpResponseBadRequest(str(e))

def api_shifts(request):
    week = request.GET.get("week")

    qs = Shift.objects.all()

    if week:
        week_date = datetime.strptime(week, "%Y-%m-%d").date()
        start = week_date
        end = week_date + timedelta(days=7)

        qs = qs.filter(date__gte=start, date__lt=end)

    data = []
    for shift in qs:
        data.append({
            "id": shift.id,
            "date": str(shift.date),
            "start": shift.start_time.strftime("%H:%M"),
            "end": shift.end_time.strftime("%H:%M"),
            "trainer": str(shift.trainer),
            "trainer_id": str(shift.trainer.id),
            "team": shift.trainer.team if hasattr(shift.trainer, "team") else "",
        })

    return JsonResponse({"shifts": data})


@login_required
@user_passes_test(is_admin)
@require_POST
def auto_schedule(request):
    """
    Admin posts:
      {"start_date":"2025-01-13","end_date":"2025-05-02","slot_start":"09:00","slot_end":"12:00","weekdays":[0,1,2,3,4]}
    """
    try:
        p = json.loads(request.body.decode("utf-8"))
        start = parse_date(p["start_date"])
        end   = parse_date(p["end_date"])
        sH, sM = map(int, p["slot_start"].split(":"))
        eH, eM = map(int, p["slot_end"].split(":"))
        slot_start = dt.time(sH, sM)
        slot_end   = dt.time(eH, eM)
        weekdays   = p.get("weekdays", [0,1,2,3,4])

        if not (start and end):
            return HttpResponseBadRequest("Invalid dates")
        if slot_end <= slot_start:
            return HttpResponseBadRequest("slot_end must be after slot_start")

        trainers = list(User.objects.filter(groups__name="Trainer").order_by("id").distinct())
        if not trainers:
            return HttpResponseBadRequest("No trainers found")

        unav = {t.id: list(Unavailability.objects.filter(trainer=t)) for t in trainers}

        created = 0
        for day in daterange(start, end):
            if day.weekday() not in weekdays:
                continue
            for t in trainers:
                has_conflict = any(
                    (u.weekday == day.weekday()) and overlaps(slot_start, slot_end, u.start_time, u.end_time)
                    for u in unav[t.id]
                )
                if not has_conflict:
                    Shift.objects.get_or_create(
                        date=day, start_time=slot_start, end_time=slot_end, trainer=t,
                        defaults={"team": ""},
                    )
                    created += 1
                    break

        return JsonResponse({"ok": True, "created": created})
    except Exception as e:
        return HttpResponseBadRequest(str(e))
    

@login_required
@user_passes_test(is_admin)
def window_status(request):
    w, _ = ScheduleWindow.objects.get_or_create(id=1)
    return JsonResponse({"is_open": w.is_open})

@login_required
@user_passes_test(is_admin)
@require_POST
def window_set(request):
    p = json.loads(request.body.decode("utf-8"))
    w, _ = ScheduleWindow.objects.get_or_create(id=1)
    w.is_open = bool(p.get("is_open", True))
    w.save()
    return JsonResponse({"ok": True, "is_open": w.is_open})

@login_required
@user_passes_test(is_admin)
def export_ics(request):
    items = Shift.objects.select_related("trainer").order_by("date","start_time")
    lines = ["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//Hatchery//Schedule//EN"]
    for s in items:
        from datetime import datetime as _dt
        dt_start = _dt.combine(s.date, s.start_time).strftime("%Y%m%dT%H%M%S")
        dt_end   = _dt.combine(s.date, s.end_time).strftime("%Y%m%dT%H%M%S")
        summary  = f"{s.team or 'Team'} - {s.trainer}"
        lines += ["BEGIN:VEVENT", f"DTSTART:{dt_start}", f"DTEND:{dt_end}", f"SUMMARY:{summary}", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    data = "\r\n".join(lines)
    resp = HttpResponse(data, content_type="text/calendar")
    resp["Content-Disposition"] = 'attachment; filename="semester_schedule.ics"'
    return resp


@login_required
def get_semesters(request):
    """Get list of semesters (generated dynamically based on current date)"""
    today = date.today()
    current_year = today.year
    current_month = today.month
    
    semesters = []
    
    # Generate semesters for current and future academic years only
    # Fall semester: August - December
    # Spring semester: January - May (starts second week of January)
    
    # Current Fall
    fall_start = date(current_year, 8, 31)
    fall_end = date(current_year, 12, 18)
    semesters.append({
        "key": f"fall{current_year}",
        "name": f"Fall {current_year}",
        "start": fall_start.isoformat(),
        "end": fall_end.isoformat()
    })
    
    # Next Spring (second week of January)
    jan_1 = date(current_year + 1, 1, 1)
    days_since_monday = jan_1.weekday()
    first_monday = jan_1 - timedelta(days=days_since_monday)
    spring_start = first_monday + timedelta(days=7)  # Second week
    spring_end = date(current_year + 1, 5, 17)
    semesters.append({
        "key": f"spring{current_year + 1}",
        "name": f"Spring {current_year + 1}",
        "start": spring_start.isoformat(),
        "end": spring_end.isoformat()
    })
    
    # Next Fall
    fall_start_next = date(current_year + 1, 8, 31)
    fall_end_next = date(current_year + 1, 12, 18)
    semesters.append({
        "key": f"fall{current_year + 1}",
        "name": f"Fall {current_year + 1}",
        "start": fall_start_next.isoformat(),
        "end": fall_end_next.isoformat()
    })
    
    # Sort by start date
    semesters.sort(key=lambda x: x["start"])
    
    return JsonResponse({"semesters": semesters})


@login_required
def get_weeks(request):
    """Get list of weeks - accessible to all authenticated users"""
    """Get list of weeks for a given semester"""
    semester_key = request.GET.get("semester")
    
    if not semester_key:
        return JsonResponse({"weeks": []})
    
    # Parse semester key (e.g., "fall2025", "spring2026")
    import re
    match = re.match(r"(fall|spring)(\d{4})", semester_key)
    if not match:
        return JsonResponse({"weeks": []})
    
    term, year_str = match.groups()
    year = int(year_str)
    
    if term == "fall":
        # Fall: August 31 to December 15
        start_date = date(year, 8, 31)
        end_date = date(year, 12, 15)
    else:  # spring
        # Spring: Second week of January to May 23
        jan_1 = date(year, 1, 1)
        days_since_monday = jan_1.weekday()
        first_monday = jan_1 - timedelta(days=days_since_monday)
        start_date = first_monday + timedelta(days=7)  # Second week
        end_date = date(year, 5, 23)
    
    # Generate weeks (Monday to Sunday)
    weeks = []
    current = start_date
    
    # Find the Monday of the week containing start_date
    days_since_monday = current.weekday()
    if days_since_monday != 0:  # Not Monday
        current = current - timedelta(days=days_since_monday)
    
    week_num = 1
    while current <= end_date:
        week_end = current + timedelta(days=6)
        if week_end > end_date:
            week_end = end_date
        
        # Format: "Week 1: Aug 31 – Sep 6"
        start_str = current.strftime("%b %d")
        end_str = week_end.strftime("%b %d")
        weeks.append({
            "value": current.isoformat(),
            "label": f"Week {week_num}: {start_str} – {end_str}"
        })
        
        current += timedelta(days=7)
        week_num += 1
    
    return JsonResponse({"weeks": weeks})


@login_required
def get_trainers(request):
    """Get list of trainers - accessible to all authenticated users"""
    """Get list of trainers with their weekly hours and specialties"""
    week_start = request.GET.get("week")
    
    # Get trainers (Team Members or Staff)
    trainers = User.objects.filter(role__in=['Team Member', 'Staff']).distinct()
    
    trainer_data = []
    for trainer in trainers:
        # Calculate weekly hours for the selected week
        hours = 0
        if week_start:
            try:
                week_date = datetime.strptime(week_start, "%Y-%m-%d").date()
                week_end = week_date + timedelta(days=7)
                shifts = Shift.objects.filter(
                    trainer=trainer,
                    date__gte=week_date,
                    date__lt=week_end
                )
                # Calculate total hours
                for shift in shifts:
                    start_dt = datetime.combine(shift.date, shift.start_time)
                    end_dt = datetime.combine(shift.date, shift.end_time)
                    hours += (end_dt - start_dt).total_seconds() / 3600
            except:
                pass
        
        # Get specialties (placeholder - you may need to adjust based on your model)
        specialties = "All Equipment"  # Default
        
        trainer_data.append({
            "id": str(trainer.id),
            "name": trainer.get_full_name() or trainer.email,
            "email": trainer.email,
            "hours": round(hours, 1),
            "specialties": specialties
        })
    
    return JsonResponse({"trainers": trainer_data})