"""
Generate Trainings for The Hatchery
====================================

Run with: python manage.py shell < generate_trainings.py
Or copy/paste into Django shell.
"""

# Training data organized by category
# Format: (level, name)
TRAINING_DATA = {
    'Laser': [
        (1, 'Laser Cutting Basics Training'),
        (2, 'Laser Cutter Rotary Training'),
        (2, 'Multi-Surface UV Printer Training'),
    ],
    'Vinyl': [
        (1, 'Vinyl Cutting Basics Training'),
        (2, 'Direct-to-Garment Printing Training'),
        (2, 'Sticker Printing Training'),
    ],
    'Woodworking': [
        (1, 'Woodworking Basics Training'),
        (2, 'Intermediate Woodworking Training'),
        (2, 'CNC Routing Training'),
        (3, 'Advanced Woodworking Training'),
    ],
    'Textile': [
        (1, 'Sewing Machine Basics Training'),
        (2, 'Embroidery Machine Training'),
    ],
    'Metalworking': [
        (1, 'Waterjet Cutting Training'),
    ],
    '3D Printing': [
        (1, 'Intro to 3D Printing'),
        (2, 'High-Detail Resin 3D Printing Training'),
        (2, 'Multi-Material Training'),
        (3, 'Photo-Realistic 3D Printing Training'),
    ],
    'Electronics': [
        (1, 'Circuitry Basics Training'),
        (1, 'Soldering Basics Training'),
        (2, 'Circuitry 2'),
    ],
}

def generate_trainings():
    """Generate all trainings in the database."""
    from trainings.models import Training, TrainingCategory
    
    print(f"\n{'='*60}")
    print("🎓 Generating Trainings for The Hatchery")
    print(f"{'='*60}\n")
    
    total_created = 0
    total_existing = 0
    
    for category_name, trainings in TRAINING_DATA.items():
        print(f"\n📁 {category_name}:")
        
        # Get or create the category
        category, cat_created = TrainingCategory.objects.get_or_create(
            name=category_name,
            defaults={
                'description': f'{category_name} trainings and certifications',
                'is_active': True,
            }
        )
        if cat_created:
            print(f"   ✓ Created category: {category_name}")
        
        for level, training_name in trainings:
            # Check if training already exists
            existing = Training.objects.filter(name=training_name).first()
            
            if existing:
                print(f"   - Lvl {level}: {training_name} (already exists)")
                total_existing += 1
                continue
            
            # Create the training
            training = Training.objects.create(
                name=training_name,
                category=category,
                level=level,
                description=f"Level {level} training for {category_name.lower()}",
                duration_minutes=60 if level == 1 else (90 if level == 2 else 120),
                max_participants=8 if level == 1 else (6 if level == 2 else 4),
                is_active=True,
            )
            
            print(f"   ✓ Lvl {level}: {training_name}")
            total_created += 1
    
    print(f"\n{'='*60}")
    print(f"✅ Created: {total_created} trainings")
    print(f"   Existing: {total_existing} trainings")
    print(f"   Total: {Training.objects.count()} trainings in system")
    print(f"{'='*60}\n")
    
    # Summary by category
    print("📊 Trainings by Category:")
    for category_name in TRAINING_DATA.keys():
        try:
            cat = TrainingCategory.objects.get(name=category_name)
            count = Training.objects.filter(category=cat).count()
            print(f"   {category_name}: {count} trainings")
        except TrainingCategory.DoesNotExist:
            print(f"   {category_name}: category not found")
    
    # Summary by level
    print("\n📊 Trainings by Level:")
    for level in [1, 2, 3]:
        count = Training.objects.filter(level=level).count()
        if count > 0:
            print(f"   Level {level}: {count} trainings")


def clear_trainings():
    """Clear all trainings (use with caution!)"""
    from trainings.models import Training
    
    count = Training.objects.count()
    confirm = input(f"⚠️  Delete all {count} trainings? (yes/no): ")
    
    if confirm.lower() == 'yes':
        Training.objects.all().delete()
        print(f"✓ Deleted {count} trainings")
    else:
        print("Cancelled")


if __name__ == '__main__':
    generate_trainings()
else:
    # Running in Django shell
    generate_trainings()
