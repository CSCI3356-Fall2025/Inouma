# from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required


@login_required
def machine_directory(request):
    # return HttpResponse("Hello World! I'm Home.")
    return render(request, 'machineDirectory.html')


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

def landing_page(request):
    return render(request, 'landing.html')
