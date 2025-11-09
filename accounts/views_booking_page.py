from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.text import slugify

from .models import Machine, MachineInstance

User = get_user_model()

# Defaults for known machines (used if the machine doesn't exist yet)
MACHINE_DEFAULTS = {
    "epilog-laser-fusion-pro": {
        "name": "Epilog Laser Fusion Pro",
        "category": "Laser",
        "location": "Hatch Front",
        "description": "High-power laser cutter for wood/acrylic.",
        "required_training_level": "Laser Cutting Basics",
        "default_instance_nickname": "FusionPro-1",
    },
    "prusa-i3-mk3s": {
        "name": "Prusa i3 MK3S+",
        "category": "3D Printing",
        "location": "Prototyping Studio",
        "description": "Reliable FDM 3D printer.",
        "required_training_level": "Intro to 3D Printing",
        "default_instance_nickname": "Prusa-A",
    },
    "cricut-maker-3": {
        "name": "Cricut Maker 3",
        "category": "Vinyl",
        "location": "Hatch Back",
        "description": "Desktop vinyl cutter.",
        "required_training_level": "Vinyl Cutting Basics",
        "default_instance_nickname": "Cricut-1",
    },
    "shapeoko-4-xxl-cnc": {
        "name": "Shapeoko 4 XXL CNC",
        "category": "Woodworking",
        "location": "Prototyping Shop",
        "description": "Large-format CNC router.",
        "required_training_level": "CNC Routing",
        "default_instance_nickname": "Shapeoko-XXL-1",
    },
    "electronics-workbench": {
        "name": "Electronics Workbench",
        "category": "Electronics",
        "location": "Prototyping Studio",
        "description": "Soldering and circuitry station.",
        "required_training_level": "Soldering Basics",
        "default_instance_nickname": "E-Workbench-1",
    },
    "ultimaker-s5": {
        "name": "Ultimaker S5",
        "category": "3D Printing",
        "location": "Prototyping Studio",
        "description": "Dual-extrusion FDM printer.",
        "required_training_level": "Intro to 3D Printing",
        "default_instance_nickname": "Ultimaker-S5-A",
    },
}

@login_required
def training_booking_page_by_name(request, machine_slug):
    defaults = MACHINE_DEFAULTS.get(machine_slug, None)

    if defaults:
        machine, _ = Machine.objects.get_or_create(
            name=defaults["name"],
            defaults={
                "category": defaults["category"],
                "location": defaults["location"],
                "description": defaults["description"],
                "required_training_level": defaults["required_training_level"],
            },
        )
        # Ensure an instance exists
        instance = MachineInstance.objects.filter(machine=machine).first()
        if not instance:
            instance = MachineInstance.objects.create(
                machine=machine,
                nickname=defaults["default_instance_nickname"],
                status="available",
            )
    else:
        # Fallback: try to find any machine with this slugified name
        machine = next(
            (m for m in Machine.objects.all() if slugify(m.name) == machine_slug),
            None
        )
        if not machine:
            # Make a generic machine so the page still works
            pretty = machine_slug.replace("-", " ").title()
            machine = Machine.objects.create(
                name=pretty,
                category="General",
                location="Hatchery",
                description="Auto-created from directory link.",
                required_training_level="General Orientation",
            )
        instance = MachineInstance.objects.filter(machine=machine).first()
        if not instance:
            instance = MachineInstance.objects.create(
                machine=machine,
                nickname=f"{slugify(machine.name)}-1",
                status="available",
            )

    # Trainers: staff users (adjust if you have a Role field)
    trainers = User.objects.filter(is_staff=True)

    return render(request, "training_booking.html", {
        "machine": machine,
        "machine_instance": instance,
        "trainers": trainers,
    })
