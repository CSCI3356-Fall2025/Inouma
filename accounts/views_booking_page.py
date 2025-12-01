from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction, models
from django.shortcuts import render
from django.utils.text import slugify
from django.views.decorators.clickjacking import xframe_options_exempt

from .models import Machine, MachineInstance

User = get_user_model()

MACHINE_DEFAULTS = {
    "epilog-laser-fusion-pro": {
        "name": "Epilog Laser Fusion Pro",
        "category": "Laser",
        "location": "Hatch Front",
        "description": "High-power laser cutter for wood/acrylic.",
        "required_training_label": "Laser Cutting Basics",
        "default_instance_nickname": "FusionPro-1",
    },
    "prusa-i3-mk3s": {
        "name": "Prusa i3 MK3S+",
        "category": "3D Printing",
        "location": "Prototyping Studio",
        "description": "Reliable FDM 3D printer.",
        "required_training_label": "Intro to 3D Printing",
        "default_instance_nickname": "Prusa-A",
    },
    "cricut-maker-3": {
        "name": "Cricut Maker 3",
        "category": "Vinyl",
        "location": "Hatch Back",
        "description": "Desktop vinyl cutter.",
        "required_training_label": "Vinyl Cutting Basics",
        "default_instance_nickname": "Cricut-1",
    },
    "shapeoko-4-xxl-cnc": {
        "name": "Shapeoko 4 XXL CNC",
        "category": "Woodworking",
        "location": "Prototyping Shop",
        "description": "Large-format CNC router.",
        "required_training_label": "CNC Routing",
        "default_instance_nickname": "Shapeoko-XXL-1",
    },
    "electronics-workbench": {
        "name": "Electronics Workbench",
        "category": "Electronics",
        "location": "Prototyping Studio",
        "description": "Soldering and circuitry station.",
        "required_training_label": "Soldering Basics",
        "default_instance_nickname": "E-Workbench-1",
    },
    "ultimaker-s5": {
        "name": "Ultimaker S5",
        "category": "3D Printing",
        "location": "Prototyping Studio",
        "description": "Dual-extrusion FDM printer.",
        "required_training_label": "Intro to 3D Printing",
        "default_instance_nickname": "Ultimaker-S5-A",
    },
}


def _set_required_training_level(machine, label: str):
    """
    Assigns Machine.required_training_level in a schema-agnostic way:
    - IntegerField with choices: map label->value; else pick the first choice.
    - ForeignKey: get_or_create by `name=<label>` if that field exists.
    - CharField/TextField: set the string directly.
    - Otherwise: skip quietly.
    """
    try:
        field = machine._meta.get_field("required_training_level")
    except Exception:
        return  # field doesn't exist in this schema

    # Integer choices
    if isinstance(field, (models.IntegerField, models.PositiveSmallIntegerField, models.SmallIntegerField)):
        choices = getattr(field, "choices", None)
        if choices:
            value = None
            low = (label or "").strip().lower()
            for val, disp in choices:
                if str(disp).strip().lower() == low:
                    value = val
                    break
            if value is None:
                # pick the FIRST available choice as a safe default
                value = next(iter(choices))[0]
            setattr(machine, "required_training_level", value)
            machine.save(update_fields=["required_training_level"])
        return

    # ForeignKey to something like TrainingLevel/Course
    if isinstance(field, models.ForeignKey):
        Rel = field.remote_field.model
        # try common field 'name'
        if hasattr(Rel, "objects"):
            if hasattr(Rel, "_meta") and "name" in [f.name for f in Rel._meta.get_fields() if hasattr(f, "name")]:
                obj, _ = Rel.objects.get_or_create(name=label or "General Orientation")
            else:
                # if there is no 'name' field, just bail out quietly
                return
            setattr(machine, "required_training_level", obj)
            machine.save(update_fields=["required_training_level"])
        return

    # Char/Text fields
    if isinstance(field, (models.CharField, models.TextField)):
        setattr(machine, "required_training_level", label or "General Orientation")
        machine.save(update_fields=["required_training_level"])
        return

    # Any other field types – skip
    return


@xframe_options_exempt
@login_required
def training_booking_page_by_name(request, machine_slug):
    """
    Teammate-proof booking page:
    - Creates Machine if missing (safe fields only).
    - Sets required_training_level using schema-aware helper above.
    - Ensures at least one MachineInstance exists.
    - Supports 'embedded' mode for iframe use (no global nav).
    """
    # NEW: detect whether this is being loaded inside the modal iframe
    embedded = request.GET.get("embedded") == "1"

    defaults = MACHINE_DEFAULTS.get(machine_slug)
    if defaults:
        name = defaults["name"]
        # Create with only fields that are very likely CharFields
        machine, created = Machine.objects.get_or_create(
            name=name,
            defaults={
                "category": defaults.get("category", "General"),
                "location": defaults.get("location", "Hatchery"),
                "description": defaults.get("description", "Auto-created from directory link."),
            },
        )
        # Now set required_training_level robustly
        _set_required_training_level(machine, defaults.get("required_training_label", "General Orientation"))

        # Ensure at least one instance
        instance = MachineInstance.objects.filter(machine=machine).first()
        if not instance:
            # status may be a choices field in some schemas; if so, fallback to raw string or first choice
            try:
                instance = MachineInstance.objects.create(
                    machine=machine,
                    nickname=defaults.get("default_instance_nickname", f"{slugify(name)}-1"),
                    status="available",
                )
            except (IntegrityError, ValueError):
                # status likely a choices int; try without status so model default applies
                instance = MachineInstance.objects.create(
                    machine=machine,
                    nickname=defaults.get("default_instance_nickname", f"{slugify(name)}-1"),
                )

    else:
        # Fallback for unknown slugs: create a generic Machine and instance
        pretty = machine_slug.replace("-", " ").title()
        machine, _ = Machine.objects.get_or_create(
            name=pretty,
            defaults={
                "category": "General",
                "location": "Hatchery",
                "description": "Auto-created from directory link.",
            },
        )
        _set_required_training_level(machine, "General Orientation")
        instance = MachineInstance.objects.filter(machine=machine).first()
        if not instance:
            instance = MachineInstance.objects.create(
                machine=machine,
                nickname=f"{slugify(machine.name)}-1",
            )

    # Trainers list
    trainers = User.objects.filter(is_staff=True)

    return render(request, "training_booking.html", {
        "machine": machine,
        "machine_instance": instance,
        "trainers": trainers,
        "embedded": embedded,  
    })
