import datetime as dt
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
            week_end = week_start + dt.timedelta(days=6)
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