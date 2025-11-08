from django.shortcuts import render, get_object_or_404
from django.contrib.auth import get_user_model
from .models import Machine, MachineInstance
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

User = get_user_model()

@login_required
def training_booking_page(request, machine_id):
    machine = get_object_or_404(Machine, id=machine_id)
    instance = MachineInstance.objects.filter(machine=machine).first()

    trainers = User.objects.filter(is_staff=True)
    return render(request, "training_booking.html", {
        "machine": machine,
        "machine_instance": instance,
        "trainers": trainers,
    })
