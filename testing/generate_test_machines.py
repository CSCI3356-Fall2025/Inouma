"""
Generate Random Machines for Testing
=====================================

Run with: python manage.py shell < testing/generate_test_machines.py
Or: python manage.py runscript generate_test_machines (if using django-extensions)

SETUP:
1. Place machine images in: static/images/machines/
   - 3DPrinter.png
   - LaserCutter.png
   - TableSaw.jpg
   - SewingMachine.png
   - CNCMachine.jpg
   - VinylCutter.jpg
   - Soldering.jpg

2. Run this script from Django shell
"""

import random
import os
from django.conf import settings
from django.core.files import File

# Machine types by category with realistic counts
MACHINE_DATA = {
    '3D Printing': [
        ('Ultimaker S5', 4),
        ('Prusa MK3S+', 8),
        ('Stratasys F170', 1),
        ('Formlabs Form 3', 3),
        ('Creality Ender 3', 6),
        ('Raise3D Pro2', 2),
        ('Bambu Lab X1E', 3),
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
        ('Bernette Sewing Machine', 3),
    ],
    'Metalworking': [
        ('Miller TIG Welder', 2),
        ('Lincoln MIG Welder', 2),
        ('Bridgeport Mill', 1),
        ('South Bend Lathe', 1),
        ('Plasma Cutter', 1),
        ('Angle Grinder Station', 3),
        ('CNC Lathe', 2),
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

# Map categories to image filenames
# Place these images in: static/images/machines/
CATEGORY_IMAGES = {
    '3D Printing': '3DPrinter.png',
    'Laser': 'LaserCutter.png',
    'Woodworking': 'TableSaw.jpg',
    'Textile': 'SewingMachine.png',
    'Metalworking': 'CNCMachine.jpg',
    'Vinyl': 'VinylCutter.jpg',
    'Electronics': 'Soldering.jpg',
}

# Alternative: Map specific machine types to specific images if desired
MACHINE_TYPE_IMAGES = {
    # Add specific overrides here if needed
    # 'Ultimaker S5': '3DPrinter.png',
    # 'SawStop Table Saw': 'TableSaw.jpg',
}


def get_image_path(category, machine_name=None):
    """
    Get the full path to the image file for a category or machine type.
    Returns None if image doesn't exist.
    """
    # Check for machine-specific image first
    if machine_name and machine_name in MACHINE_TYPE_IMAGES:
        filename = MACHINE_TYPE_IMAGES[machine_name]
    else:
        filename = CATEGORY_IMAGES.get(category)
    
    if not filename:
        return None
    
    # Try multiple possible locations
    possible_paths = [
        os.path.join(settings.BASE_DIR, 'static', 'images', 'machines', filename),
        os.path.join(settings.BASE_DIR, 'staticfiles', 'images', 'machines', filename),
        os.path.join(settings.STATIC_ROOT or '', 'images', 'machines', filename) if settings.STATIC_ROOT else None,
        os.path.join(settings.BASE_DIR, 'media', 'machine_images', filename),
    ]
    
    for path in possible_paths:
        if path and os.path.exists(path):
            return path
    
    return None


def generate_random_pin_position():
    """
    Generate a random position for the machine pin on a floorplan.
    Returns (x, y) as percentages (0-100).
    Keeps pins away from edges and clusters them in realistic working areas.
    """
    # Define "zones" where machines might be placed
    # Avoid edges (10% margin) and create some clustering
    
    # Random zone selection for variety
    zone = random.choice(['center', 'left', 'right', 'top', 'bottom'])
    
    if zone == 'center':
        x = random.uniform(30, 70)
        y = random.uniform(30, 70)
    elif zone == 'left':
        x = random.uniform(15, 40)
        y = random.uniform(20, 80)
    elif zone == 'right':
        x = random.uniform(60, 85)
        y = random.uniform(20, 80)
    elif zone == 'top':
        x = random.uniform(20, 80)
        y = random.uniform(15, 40)
    else:  # bottom
        x = random.uniform(20, 80)
        y = random.uniform(60, 85)
    
    return round(x, 2), round(y, 2)


def generate_machines():
    """Generate test machines in the database with images and pin positions."""
    from machines.models import Machine, MachineCategory
    from locations.models import Location
    
    # Get all locations (to distribute machines across them)
    locations = list(Location.objects.all())
    
    if not locations:
        print("❌ No locations found! Please create at least one location first.")
        print("   Run: python manage.py shell")
        print("   >>> from locations.models import Location")
        print("   >>> Location.objects.create(name='Main Workshop', floor='1st Floor', building='Engineering')")
        return
    
    print(f"Found {len(locations)} location(s): {', '.join([l.name for l in locations])}")
    print(f"\n{'='*60}")
    print("🔧 Generating Test Machines with Images & Pin Positions")
    print(f"{'='*60}\n")
    
    total_created = 0
    images_assigned = 0
    pins_assigned = 0
    
    for category, machine_types in MACHINE_DATA.items():
        print(f"\n📁 {category}:")
        
        # Get or create category
        cat_obj, cat_created = MachineCategory.objects.get_or_create(
            name=category,
            defaults={
                'description': f'{category} equipment',
                'is_active': True,
            }
        )
        
        # Assign image to category if it has an image field and no image yet
        if hasattr(cat_obj, 'image') and not cat_obj.image:
            image_path = get_image_path(category)
            if image_path:
                try:
                    with open(image_path, 'rb') as img_file:
                        cat_obj.image.save(
                            CATEGORY_IMAGES[category],
                            File(img_file),
                            save=True
                        )
                    print(f"   📷 Category image assigned: {CATEGORY_IMAGES[category]}")
                except Exception as e:
                    print(f"   ⚠️  Could not assign category image: {e}")
        
        for machine_name, count in machine_types:
            created_count = 0
            
            for i in range(1, count + 1):
                # Create unique identifier
                name = f"{machine_name} #{i}"
                
                # Check if already exists
                if Machine.objects.filter(name=name, machine_name=machine_name).exists():
                    continue
                
                # Select a location (distribute across locations)
                location = random.choice(locations)
                
                # Generate random pin position
                pin_x, pin_y = generate_random_pin_position()
                
                # Create machine
                machine_data = {
                    'name': name,
                    'machine_name': machine_name,
                    'category': category,
                    'location': location,
                    'description': f"{machine_name} - Unit {i}. Available for student use with proper training.",
                    'year_bought': random.randint(2018, 2024),
                    'manufacturer': '',
                    'model_number': '',
                    'documentation_url': '',
                    'mac_address': '',
                }
                
                # Add pin position if model supports it
                machine_data['map_position_x'] = pin_x
                machine_data['map_position_y'] = pin_y
                
                try:
                    machine = Machine.objects.create(**machine_data)
                    pins_assigned += 1
                except TypeError:
                    # If map_position fields don't exist, create without them
                    del machine_data['map_position_x']
                    del machine_data['map_position_y']
                    machine = Machine.objects.create(**machine_data)
                
                # Assign image to machine
                image_path = get_image_path(category, machine_name)
                if image_path and hasattr(machine, 'image'):
                    try:
                        with open(image_path, 'rb') as img_file:
                            # Create unique filename for each machine
                            ext = os.path.splitext(image_path)[1]
                            img_filename = f"{machine_name.replace(' ', '_').replace('#', '')}_{i}{ext}"
                            machine.image.save(img_filename, File(img_file), save=True)
                        images_assigned += 1
                    except Exception as e:
                        print(f"      ⚠️  Image error for {name}: {e}")
                
                # Set category FK if model has it
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
    print(f"✅ Generation Complete!")
    print(f"   • Machines created: {total_created}")
    print(f"   • Images assigned: {images_assigned}")
    print(f"   • Pin positions set: {pins_assigned}")
    print(f"{'='*60}\n")
    
    # Summary
    print("📊 Machine Summary by Category:")
    for category in MACHINE_DATA.keys():
        count = Machine.objects.filter(category=category).count()
        types = Machine.objects.filter(category=category).values('machine_name').distinct().count()
        print(f"   {category}: {count} machines ({types} types)")
    
    print(f"\n   Total: {Machine.objects.count()} machines")
    
    # Check for images
    print(f"\n📷 Image Status:")
    with_images = Machine.objects.exclude(image='').exclude(image__isnull=True).count()
    without_images = Machine.objects.filter(image='').count() + Machine.objects.filter(image__isnull=True).count()
    print(f"   With images: {with_images}")
    print(f"   Without images: {without_images}")
    
    if without_images > 0:
        print(f"\n   💡 To add images, place files in: static/images/machines/")
        print(f"      Expected files: {', '.join(CATEGORY_IMAGES.values())}")


def update_existing_machines_with_images_and_pins():
    """
    Update existing machines that are missing images or pin positions.
    Run this after generate_machines() if you added images later.
    """
    from machines.models import Machine
    
    print("🔄 Updating existing machines...")
    
    updated_images = 0
    updated_pins = 0
    
    for machine in Machine.objects.all():
        changed = False
        
        # Update image if missing
        if hasattr(machine, 'image') and not machine.image:
            image_path = get_image_path(machine.category, machine.machine_name)
            if image_path:
                try:
                    with open(image_path, 'rb') as img_file:
                        ext = os.path.splitext(image_path)[1]
                        img_filename = f"{machine.machine_name.replace(' ', '_')}_{machine.id}{ext}"
                        machine.image.save(img_filename, File(img_file), save=False)
                    updated_images += 1
                    changed = True
                except Exception as e:
                    print(f"   ⚠️  Error updating image for {machine.name}: {e}")
        
        # Update pin position if missing
        if hasattr(machine, 'map_position_x'):
            if machine.map_position_x is None or machine.map_position_x == 0:
                pin_x, pin_y = generate_random_pin_position()
                machine.map_position_x = pin_x
                machine.map_position_y = pin_y
                updated_pins += 1
                changed = True
        
        if changed:
            machine.save()
    
    print(f"✅ Updated {updated_images} images and {updated_pins} pin positions")


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


def show_image_setup_instructions():
    """Print instructions for setting up images."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    IMAGE SETUP INSTRUCTIONS                   ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  1. Create the directory:                                    ║
║     mkdir -p static/images/machines                          ║
║                                                              ║
║  2. Place these images in the directory:                     ║
║     • 3DPrinter.png      (for 3D Printing category)          ║
║     • LaserCutter.png    (for Laser category)                ║
║     • TableSaw.jpg       (for Woodworking category)          ║
║     • SewingMachine.png  (for Textile category)              ║
║     • CNCMachine.jpg     (for Metalworking category)         ║
║     • VinylCutter.jpg    (for Vinyl category)                ║
║     • Soldering.jpg      (for Electronics category)          ║
║                                                              ║
║  3. Run this script: 
          python manage.py shell -c "from machines.models import Machine; Machine.objects.all().delete(); print('Cleared!')"                                        ║
║     python manage.py shell < testing/generate_test_machines.py║
║                                                              ║
║  4. If machines already exist, update them:                  ║
║     >>> from testing.generate_test_machines import *         ║
║     >>> update_existing_machines_with_images_and_pins()      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")


# Entry point when running script
if __name__ == '__main__':
    generate_machines()
else:
    # Running in Django shell
    print("\n🔧 Machine Generator Loaded!")
    print("   • generate_machines() - Create test machines")
    print("   • update_existing_machines_with_images_and_pins() - Update existing")
    print("   • clear_test_machines() - Delete all machines")
    print("   • show_image_setup_instructions() - Setup help")
    print("")
    
    # Auto-run generation
    generate_machines()