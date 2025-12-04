"""
Link Machines to Training Requirements
======================================

Links machines to their required trainings so the reservation system
can check if users have completed the required training.

Usage:
    python manage.py shell < testing/link_machines_to_trainings.py
"""

from machines.models import Machine, Training, MachineCategory


def link_machines_to_trainings():
    """Link machines to their required trainings based on category."""
    
    print("=" * 60)
    print("LINKING MACHINES TO TRAINING REQUIREMENTS")
    print("=" * 60)
    
    # Map categories to training names
    # Format: category_name -> list of training names that apply
    CATEGORY_TRAINING_MAP = {
        '3D Printing': ['Intro to 3D Printing'],
        'Laser': ['Laser Cutting Basics Training'],
        'Woodworking': ['Woodworking Basics Training'],
        'Textile': ['Sewing Machine Basics Training'],
        'Metalworking': ['Waterjet Cutting Training'],
        'Vinyl': ['Vinyl Cutting Basics Training'],
        'Electronics': ['Circuitry Basics Training', 'Soldering Basics Training'],
    }
    
    linked_count = 0
    
    # Get all machines
    machines = Machine.objects.all()
    print(f"\n📋 Processing {machines.count()} machines...")
    
    for machine in machines:
        # Get machine category
        # category is a CharField (string), category_fk is a ForeignKey
        category_name = None
        if machine.category_fk:
            category_name = machine.category_fk.name
        elif machine.category:
            # category is already a string
            category_name = machine.category
        
        if not category_name:
            continue
        
        # Find trainings for this category
        training_names = CATEGORY_TRAINING_MAP.get(category_name, [])
        
        if not training_names:
            continue
        
        # Update each training to include this machine's machine_name
        for training_name in training_names:
            try:
                training = Training.objects.get(name=training_name, status='active')
                
                # Get current machine_type_names list
                machine_type_names = training.machine_type_names or []
                
                # Add machine's machine_name if not already there
                if machine.machine_name and machine.machine_name not in machine_type_names:
                    machine_type_names.append(machine.machine_name)
                    training.machine_type_names = machine_type_names
                    training.save()
                    linked_count += 1
                    print(f"   ✓ Linked {machine.name} → {training.name}")
            except Training.DoesNotExist:
                print(f"   ⚠️  Training '{training_name}' not found (skipping {machine.name})")
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"\n✅ Linked {linked_count} machine-training pairs")
    print("\nNow machines will check for training requirements when users try to reserve them.")
    print("=" * 60)
    print()


if __name__ == '__main__':
    link_machines_to_trainings()
else:
    # Running in Django shell
    link_machines_to_trainings()

