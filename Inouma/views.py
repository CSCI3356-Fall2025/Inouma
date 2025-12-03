from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages

from datetime import date, datetime

from accounts.models import Certification, TrainingReservation
from machines.models import Machine
from scheduling.models import Shift, Semester, Unavailability
from django.utils import timezone
# from scheduling.models import Reservation




# @login_required
# def machine_directory(request):
#     # return HttpResponse("Hello World! I'm Home.")
#     return render(request, 'machineDirectory.html')


@login_required
def my_reservations(request):
    """
    Display user's reservations and training sessions
    """
    context = {
        # In a real app, you'd query the database here
        # For now, the template has hardcoded prototype data
    }
    return render(request, 'myReservations.html', context)


@staff_member_required
def staff_dashboard(request):
    """
    Staff dashboard for managing machines, locations, and schedules
    """
    context = {
        # In a real app, you'd query the database here
        # For now, the template has hardcoded prototype data
    }
    return render(request, 'staffDashboard.html', context)

@login_required
def user_dashboard(request):
    certifications = Certification.objects.filter(user=request.user)
    training_sessions = TrainingReservation.objects.filter(
        student=request.user
    ).order_by('start_time')

    context = {
        "certifications": certifications,
        "training_sessions": training_sessions,
        "today": date.today(),
        "now": datetime.now(),
    }
    return render(request, "userDashboard.html", context)


@login_required
def trainer_dashboard(request):
    """
    Dashboard for trainers to quickly access schedule and availability tools.
    """
    # Allow trainers, team leads (auto-trainers), or staff
    is_trainer = (
        getattr(request.user, "is_trainer", False)
        or getattr(request.user, "is_team_lead", False)
    )
    team_profile = getattr(request.user, "team_profile", None)
    if team_profile:
        is_trainer = is_trainer or getattr(team_profile, "is_trainer", False) or getattr(team_profile, "is_team_lead", False)

    if not is_trainer and not request.user.is_staff:
        messages.error(request, "Trainer access required.")
        return redirect("user_dashboard")

    active_semester = Semester.objects.filter(is_active=True).first()
    upcoming_shifts = []
    unavailability_blocks = []

    if active_semester:
        shifts_qs = Shift.objects.filter(user=request.user, semester=active_semester).order_by("date", "start_time")
        upcoming_shifts = shifts_qs.filter(date__gte=timezone.now().date())[:5]
        unavailability_blocks = Unavailability.objects.filter(
            user=request.user, semester=active_semester
        ).order_by("day_of_week", "start_time")

    context = {
        "active_semester": active_semester,
        "upcoming_shifts": upcoming_shifts,
        "unavailability_blocks": unavailability_blocks,
    }
    return render(request, "trainerDashboard.html", context)

def landing_page(request):
    return render(request, 'landing.html')

@require_POST
@login_required
def create_reservation_api(request, machine_id):
    machine = get_object_or_404(Machine, pk=machine_id)

    reservation_date = request.POST.get("reservation_date")
    start_time = request.POST.get("start_time")
    end_time = request.POST.get("end_time")
    purpose = request.POST.get("purpose", "")

    if not reservation_date or not start_time or not end_time:
        return JsonResponse(
            {"success": False, "error": "Missing required fields."},
            status=400,
        )

    # reservation = Reservation.objects.create(
    #     machine=machine,
    #     user=request.user,
    #     reservation_date=reservation_date,
    #     start_time=start_time,
    #     end_time=end_time,
    #     purpose=purpose,
    # )

    return JsonResponse(
        {
            "success": True,
            "message": "Reservation created.",
            # "reservation_id": reservation.id,
        }
    )
