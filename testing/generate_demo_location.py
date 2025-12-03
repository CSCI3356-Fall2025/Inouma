"""
Generate Demo Location
======================

Creates a default location for the demo environment.
Machines need to be assigned to a location, so this must be created first.

Run with:
    python manage.py shell < testing/generate_demo_location.py
"""

from locations.models import Location


def generate_demo_location():
    """Generate a default location for demo purposes."""
    
    print("=" * 60)
    print("GENERATING DEMO LOCATION")
    print("=" * 60)
    
    # Check if location already exists
    existing = Location.objects.first()
    if existing:
        print(f"\n✓ Location already exists: {existing.name}")
        print(f"   Building: {existing.building}")
        print(f"   Floor: {existing.floor}")
        print(f"   Using existing location for demo.")
        return existing
    
    # Create a default location
    print("\n📍 Creating demo location...")
    
    location = Location.objects.create(
        name='The Hatchery Makerspace',
        building='245 Beacon St',
        floor='3rd Floor',
        num_stations=20,
        capacity=50,
        machine_types='3D Printing, Laser, Woodworking, Textile, Metalworking, Vinyl, Electronics'
    )
    
    print(f"   ✓ Created: {location.name}")
    print(f"      Building: {location.building}")
    print(f"      Floor: {location.floor}")
    print(f"      Stations: {location.num_stations}")
    print(f"      Capacity: {location.capacity}")
    print(f"      Machine Types: {location.machine_types}")
    
    print("\n" + "=" * 60)
    print("✅ Demo location created successfully!")
    print("=" * 60)
    print("\nYou can now run generate_test_machines.py")
    print()
    
    return location


if __name__ == '__main__':
    generate_demo_location()
else:
    # Running in Django shell
    generate_demo_location()

