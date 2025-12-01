"""
Generate Random Machines for Testing
=====================================

Run with: python manage.py shell < generate_test_machines.py
Or copy/paste into Django shell.
"""

import random

# Machine types by category with realistic counts
MACHINE_DATA = {
    '3D Printing': [
        ('Ultimaker S5', 4),
        ('Prusa MK3S+', 8),
        ('Stratasys F170', 1),
        ('Formlabs Form 3', 3),
        ('Creality Ender 3', 6),
        ('Raise3D Pro2', 2),
    ],
    'Laser': [
        ('Epilog Fusion Pro', 3),
        ('Glowforge Pro', 2),
        ('Universal Laser VLS6.60', 1),
        ('Trotec Speedy 400', 2),
    ],
    'Woodworking': [
        ('SawStop Table Saw', 2),
        ('Laguna Bandsaw', 2),
        ('DeWalt Miter Saw', 3),
        ('Festool Domino', 1),
        ('ShopBot CNC Router', 1),
        ('Drill Press', 4),
    ],
    'Textile': [
        ('Brother SE1900', 3),
        ('Janome MC6700P', 2),
        ('Singer Heavy Duty', 4),
        ('Cricut Maker 3', 2),
        ('Heat Press', 2),
    ],
    'Metalworking': [
        ('Miller TIG Welder', 2),
        ('Lincoln MIG Welder', 2),
        ('Bridgeport Mill', 1),
        ('South Bend Lathe', 1),
        ('Plasma Cutter', 1),
        ('Angle Grinder Station', 3),
    ],
    'Vinyl': [
        ('Roland CAMM-1', 2),
        ('Cricut Explore Air', 3),
        ('Silhouette Cameo 4', 2),
        ('USCutter MH871', 1),
    ],
    'Electronics': [
        ('Soldering Station', 8),
        ('Oscilloscope', 4),
        ('Function Generator', 3),
        ('PCB Mill', 1),
        ('Reflow Oven', 1),
        ('Hot Air Rework', 2),
    ],
}

def generate_machines():
    """Generate test machines in the database."""
    from machines.models import Machine, MachineCategory
    from locations.models import Location
    
    # Get or create a default location
    location = Location.objects.first()
    if not location:
        print("❌ No locations found! Please create at least one location first.")
        return
    
    print(f"Using location: {location.name}")
    print(f"\n{'='*60}")
    print("🔧 Generating Test Machines")
    print(f"{'='*60}\n")
    
    total_created = 0
    
    for category, machine_types in MACHINE_DATA.items():
        print(f"\n📁 {category}:")
        
        # Get or create category
        cat_obj, _ = MachineCategory.objects.get_or_create(
            name=category,
            defaults={
                'description': f'{category} equipment',
                'is_active': True,
            }
        )
        
        for machine_name, count in machine_types:
            created_count = 0
            
            for i in range(1, count + 1):
                # Create unique identifier
                name = f"{machine_name} #{i}"
                
                # Check if already exists
                if Machine.objects.filter(name=name, machine_name=machine_name).exists():
                    continue
                
                # Create machine with all required fields
                machine = Machine.objects.create(
                    name=name,
                    machine_name=machine_name,
                    category=category,
                    location=location,
                    description=f"{machine_name} - Unit {i}",
                    year_bought=random.randint(2018, 2024),
                    manufacturer='',  # Empty string for NOT NULL fields
                    model_number='',
                    documentation_url='',
                    mac_address='',
                )
                
                # Set category FK if it exists
                if hasattr(machine, 'category_fk'):
                    machine.category_fk = cat_obj
                    machine.save()
                
                created_count += 1
                total_created += 1
            
            if created_count > 0:
                print(f"   ✓ {machine_name}: {created_count} machines created")
            else:
                existing = Machine.objects.filter(machine_name=machine_name).count()
                print(f"   - {machine_name}: {existing} already exist")
    
    print(f"\n{'='*60}")
    print(f"✅ Total machines created: {total_created}")
    print(f"{'='*60}\n")
    
    # Summary
    print("📊 Machine Summary by Category:")
    for category in MACHINE_DATA.keys():
        count = Machine.objects.filter(category=category).count()
        types = Machine.objects.filter(category=category).values('machine_name').distinct().count()
        print(f"   {category}: {count} machines ({types} types)")
    
    print(f"\n   Total: {Machine.objects.count()} machines")


def clear_test_machines():
    """Clear all machines (use with caution!)"""
    from machines.models import Machine
    
    count = Machine.objects.count()
    confirm = input(f"⚠️  Delete all {count} machines? (yes/no): ")
    
    if confirm.lower() == 'yes':
        Machine.objects.all().delete()
        print(f"✓ Deleted {count} machines")
    else:
        print("Cancelled")


if __name__ == '__main__':
    generate_machines()
else:
    # Running in Django shell
    generate_machines()