# from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from accounts.models import Certification, TrainingReservation
from datetime import date, datetime


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

def landing_page(request):
    return render(request, 'landing.html')
