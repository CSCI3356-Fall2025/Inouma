from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test

def is_staff_user(user):
    return user.is_staff

@user_passes_test(is_staff_user)
def schedule_management(request):
    """Schedule management page - staff only"""
    context = {
        # Add any context data you need here
    }
    return render(request, 'scheduling/semester_schedule.html', context)