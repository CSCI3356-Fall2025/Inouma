from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from .models import Machine, TrainingType
from collections import defaultdict
import json
import os
from django.conf import settings
from .utils import convert_heic_to_jpg
from locations.models import Location
from django.db import models


def is_superuser(user):
    return user.is_superuser


@login_required
def staff_dashboard(request):
    # Get all machines grouped by category
    machines = Machine.objects.all()
    machines_by_category = defaultdict(list)
    
    for machine in machines:
        machines_by_category[machine.category].append(machine)
    
    # Sort categories
    category_order = ['Laser', 'Vinyl', 'Woodworking', 'Textile', 'Metalworking', '3D Printing', 'Electronics']
    machines_by_category = {cat: machines_by_category[cat] for cat in category_order if cat in machines_by_category}
    
    # Get all unique images grouped by category
    images_by_category = defaultdict(list)
    seen_images = defaultdict(set)
    
    # Get all machines that have images (not empty and not None)
    all_machines_with_images = Machine.objects.filter(
        image__isnull=False
    ).exclude(
        image=''
    ).order_by('category', '-created_at')
    
    print(f"DEBUG: Found {all_machines_with_images.count()} machines with images")  # Debug line
    
    for machine in all_machines_with_images:
        if machine.image:
            image_name = machine.image.name
            print(f"DEBUG: Processing machine {machine.name} with image {image_name}")  # Debug line
            
            if image_name not in seen_images[machine.category]:
                images_by_category[machine.category].append({
                    'url': machine.image.url,
                    'name': image_name,
                    'machine_example': f"{machine.name} ({machine.machine_name})"
                })
                seen_images[machine.category].add(image_name)
    
    print(f"DEBUG: images_by_category = {dict(images_by_category)}")  # Debug line
    
    context = {
        'machines_by_category': machines_by_category,
        'images_by_category': dict(images_by_category),
        'category_order': category_order,
    }
    return render(request, 'staff_dashboard.html', context)


@login_required
def add_machine(request):
    if request.method == 'POST':
        # Handle image selection and validation
        image_choice = request.POST.get('image_choice')
        machine_image = None
        
        # Validate and process uploaded image
        if image_choice == 'upload' and request.FILES.get('custom_image'):
            uploaded_file = request.FILES.get('custom_image')
            
            # Check file extension
            file_name = uploaded_file.name.lower()
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            heic_extensions = ['.heic', '.heif']
            
            # Check if file is HEIC - convert it to JPG
            if any(file_name.endswith(ext) for ext in heic_extensions):
                print(f"Converting HEIC file: {uploaded_file.name}")
                converted_file = convert_heic_to_jpg(uploaded_file)
                
                if converted_file:
                    machine_image = converted_file
                    messages.success(request, f'HEIC image "{uploaded_file.name}" was automatically converted to JPG.')
                else:
                    messages.error(request, 'Failed to convert HEIC file. Please try converting it to JPG manually.')
                    return redirect('staff_dashboard')
            
            # Check if file has an allowed extension
            elif any(file_name.endswith(ext) for ext in allowed_extensions):
                # Check MIME type as an extra security measure
                allowed_mime_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
                if uploaded_file.content_type not in allowed_mime_types:
                    messages.error(request, f'Invalid file type: {uploaded_file.content_type}. Please upload a valid image file.')
                    return redirect('staff_dashboard')
                
                machine_image = uploaded_file
            
            else:
                messages.error(request, 'Invalid file format. Please upload a JPG, PNG, GIF, WebP, or HEIC image.')
                return redirect('staff_dashboard')
        
        elif image_choice == 'existing' and request.POST.get('existing_image'):
            # Copy the existing image reference
            existing_image_path = request.POST.get('existing_image')
            existing_machine = Machine.objects.filter(image=existing_image_path).first()
            if existing_machine:
                machine_image = existing_machine.image
        
        # Create the machine
        machine = Machine(
            name=request.POST.get('name'),
            machine_name=request.POST.get('machine_name'),
            category=request.POST.get('category'),
            location_id=request.POST.get('location'),  # ✅ Use location_id for ForeignKey
            description=request.POST.get('description', ''),
            mac_address=request.POST.get('mac_address', ''),
            year_bought=request.POST.get('year_bought') or None,
            requires_level_1=request.POST.get('requires_level_1') == 'on',
            requires_level_2=request.POST.get('requires_level_2') == 'on',
            requires_level_3=request.POST.get('requires_level_3') == 'on',
            map_position_x=request.POST.get('map_position_x') or None,
            map_position_y=request.POST.get('map_position_y') or None,
        )
        
        # Assign image if provided
        if machine_image:
            machine.image = machine_image
        
        machine.save()

        # Auto-assign a default training based on category (Delivery 6)
        category_default_trainings = {
            'Laser': 'Laser Cutter Training',
            '3D Printing': 'Intro to 3D Printing',
            'Vinyl': 'Vinyl Cutter Training',
            'Woodworking': 'Wood Shop Safety',
            'Textile': 'Sewing / Textile Training',
            'Metalworking': 'Metal Shop Safety',
            'Electronics': 'Electronics Bench Training',
        }

        default_name = category_default_trainings.get(machine.category)
        if default_name:
            training, _ = TrainingType.objects.get_or_create(
                name=default_name,
                defaults={
                    'description': f'Default required training for {machine.category} machines.'
                },
            )
            machine.required_trainings.add(training)

        messages.success(request, f'Machine "{machine.name}" added successfully!')
        return redirect('staff_dashboard')
    return redirect('staff_dashboard')


@user_passes_test(is_superuser)
def remove_machine(request, machine_id):
    """Delete a machine from the database"""
    if request.method == 'POST':
        try:
            machine = get_object_or_404(Machine, id=machine_id)
            machine_name = machine.machine_name
            
            # Try to delete - handle potential foreign key issues
            try:
                # Clear many-to-many relationships first
                if hasattr(machine, 'required_trainings'):
                    machine.required_trainings.clear()
                
                # Now delete the machine
                machine.delete()
                
            except Exception as delete_error:
                print(f"Delete error details: {delete_error}")
                import traceback
                print(traceback.format_exc())
                raise delete_error
            
            # Return JSON response for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Machine "{machine_name}" deleted successfully!'
                })
            
            messages.success(request, f'Machine "{machine_name}" deleted successfully!')
            return redirect('staff_machine_directory')
            
        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"Error deleting machine: {error_msg}")
            print(traceback.format_exc())
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f'Error deleting machine: {error_msg}'
                }, status=500)
            
            messages.error(request, f'Error deleting machine: {error_msg}')
            return redirect('staff_machine_directory')
    
    return redirect('staff_machine_directory')




@login_required
def get_machine_suggestions(request):
    """API endpoint to get machine type suggestions for autocomplete"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 1:
        return JsonResponse({'suggestions': []})
    
    # Get all machine names that match the query
    machines = Machine.objects.filter(
        machine_name__icontains=query
    ).values_list('machine_name', flat=True)
    
    # Manually deduplicate while preserving order and limiting to 10
    seen = set()
    unique_machines = []
    for machine in machines:
        # Normalize the machine name (strip whitespace and compare case-insensitively)
        normalized = machine.strip()
        if normalized.lower() not in seen:
            seen.add(normalized.lower())
            unique_machines.append(normalized)
            if len(unique_machines) >= 10:
                break
    
    return JsonResponse({'suggestions': unique_machines})

@login_required
def check_duplicate_machine(request):
    """API endpoint to check if a machine with the same name and type exists"""
    name = request.GET.get('name', '').strip()
    machine_name = request.GET.get('machine_name', '').strip()
    
    if not name or not machine_name:
        return JsonResponse({'duplicate': False})
    
    # Check if a machine with this exact name and type exists
    duplicate = Machine.objects.filter(name__iexact=name, machine_name__iexact=machine_name).first()
    
    if duplicate:
        return JsonResponse({
            'duplicate': True,
            'machine_name': duplicate.machine_name,
            'name': duplicate.name,
            'location': duplicate.location,
            'category': duplicate.category
        })
    
    return JsonResponse({'duplicate': False})


# Pass Machines to Machine Directory Page
@login_required
def machine_directory(request):
    """Display all machines for browsing and reservations"""
    machines = Machine.objects.all().order_by('category', 'name')
    
    context = {
        'machines': machines,
    }
    return render(request, 'machineDirectory.html', context)


@login_required
def get_search_suggestions(request):
    """API endpoint for search autocomplete suggestions"""
    query = request.GET.get('q', '').strip().lower()
    
    if len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    suggestions = []
    seen = set()
    
    try:
        # Search machine types
        machine_types = Machine.objects.filter(
            machine_name__icontains=query
        ).values_list('machine_name', flat=True).distinct()[:5]
        
        for machine_type in machine_types:
            if machine_type and machine_type.lower() not in seen:
                suggestions.append({
                    'text': machine_type,
                    'type': 'Machine Type'
                })
                seen.add(machine_type.lower())
        
        # Search machine names (IDs)
        machine_names = Machine.objects.filter(
            name__icontains=query
        ).values_list('name', flat=True).distinct()[:5]
        
        for name in machine_names:
            if name and name.lower() not in seen:
                suggestions.append({
                    'text': name,
                    'type': 'Machine ID'
                })
                seen.add(name.lower())
        
        # Search categories
        categories = Machine.objects.filter(
            category__icontains=query
        ).values_list('category', flat=True).distinct()[:3]
        
        for category in categories:
            if category and category.lower() not in seen:
                suggestions.append({
                    'text': category,
                    'type': 'Category'
                })
                seen.add(category.lower())
        
        # Search locations - need to go through the Location model
        from locations.models import Location
        location_objs = Location.objects.filter(
            name__icontains=query
        ).distinct()[:3]
        
        for loc in location_objs:
            loc_text = f"{loc.building} - {loc.name}" if loc.building else loc.name
            if loc_text.lower() not in seen:
                suggestions.append({
                    'text': loc_text,
                    'type': 'Location'
                })
                seen.add(loc_text.lower())
    
    except Exception as e:
        print(f"Error in search suggestions: {e}")
        return JsonResponse({'suggestions': []})
    
    return JsonResponse({'suggestions': suggestions[:10]})



@user_passes_test(is_superuser)
def machine_management(request):
    """Machine management page - superuser only"""
    from locations.models import Location
    
    # Get all locations with their details
    locations = Location.objects.all()
    
    # For each location, get machines that are already placed there
    locations_data = []
    for location in locations:
        # Get machines at this location with map positions
        machines_at_location = Machine.objects.filter(
            location=str(location.id)
        ).exclude(
            map_position_x__isnull=True
        ).exclude(
            map_position_y__isnull=True
        )
        
        location_machines = [{
            'id': m.id,
            'name': m.name,
            'machine_name': m.machine_name,
            'category': m.category,
            'x': float(m.map_position_x),
            'y': float(m.map_position_y)
        } for m in machines_at_location]
        
        locations_data.append({
            'id': location.id,
            'name': location.name,
            'building': location.building,
            'floor': location.floor,
            'machine_types': location.get_machine_types_list(),
            'num_stations': location.num_stations,
            'capacity': location.capacity,
            'has_floorplan': bool(location.floorplan_image),
            'floorplan_url': location.floorplan_image.url if location.floorplan_image else '',
            'machines': location_machines
        })
    
    # Get all unique images grouped by category
    images_by_category = defaultdict(list)
    seen_images = defaultdict(set)
    
    all_machines_with_images = Machine.objects.filter(
        image__isnull=False
    ).exclude(
        image=''
    ).order_by('category', '-created_at')
    
    for machine in all_machines_with_images:
        if machine.image:
            image_name = machine.image.name
            
            if image_name not in seen_images[machine.category]:
                images_by_category[machine.category].append({
                    'url': machine.image.url,
                    'name': image_name,
                    'machine_example': f"{machine.name} ({machine.machine_name})"
                })
                seen_images[machine.category].add(image_name)
    
    category_order = ['Laser', 'Vinyl', 'Woodworking', 'Textile', 'Metalworking', '3D Printing', 'Electronics']
    
    context = {
        'locations': locations,
        'locations_data_json': json.dumps(locations_data),  # Convert to JSON string for JavaScript
        'images_by_category': dict(images_by_category),
        'category_order': category_order,
    }
    return render(request, 'machines/add_machine_form.html', context)

@login_required
def machine_directory(request):
    """Display category overview - Level 1"""
    # Get count of machines per category
    categories = Machine.objects.values('category').annotate(
        count=models.Count('id')
    ).order_by('category')
    
    category_order = ['Laser', 'Vinyl', 'Woodworking', 'Textile', 'Metalworking', '3D Printing', 'Electronics']
    
    # Create structured data
    category_data = []
    for cat in category_order:
        cat_info = next((c for c in categories if c['category'] == cat), None)
        if cat_info:
            # Get a sample image from this category
            sample_machine = Machine.objects.filter(category=cat, image__isnull=False).exclude(image='').first()
            category_data.append({
                'name': cat,
                'count': cat_info['count'],
                'image': sample_machine.image.url if sample_machine else None
            })
    
    context = {
        'categories': category_data,
    }
    return render(request, 'machines/category_overview.html', context)


@login_required
def category_detail(request, category):
    """Display machine types within a category - Level 2"""
    # Get unique machine types in this category
    machine_types = Machine.objects.filter(category=category).values('machine_name').annotate(
        count=models.Count('id')
    ).order_by('machine_name')
    
    # Get sample image for each machine type
    types_data = []
    for mt in machine_types:
        sample = Machine.objects.filter(
            category=category, 
            machine_name=mt['machine_name'],
            image__isnull=False
        ).exclude(image='').first()
        
        types_data.append({
            'name': mt['machine_name'],
            'count': mt['count'],
            'image': sample.image.url if sample else None
        })
    
    context = {
        'category': category,
        'machine_types': types_data,
    }
    return render(request, 'machines/category_detail.html', context)


@login_required
def machine_type_detail(request, machine_type):
    """Display individual machines of a specific type - Level 3"""
    machines = Machine.objects.filter(machine_name=machine_type).order_by('name')
    
    context = {
        'machine_type': machine_type,
        'machines': machines,
        'category': machines.first().category if machines else None,
    }
    return render(request, 'machines/machine_type_detail.html', context)


@login_required
def machine_detail(request, machine_id):
    """Display full machine details with floorplan - Level 4"""
    from locations.models import Location
    from django.contrib.auth import get_user_model
    from datetime import date
    
    User = get_user_model()
    machine = get_object_or_404(Machine, id=machine_id)
    
    # Since we migrated to ForeignKey, location access is now direct
    location = machine.location
    has_floorplan = bool(location.floorplan_image) if location else False
    floorplan_url = location.floorplan_image.url if has_floorplan else None
    
    # Get other machines at this location
    other_machines = []
    if location:
        other_machines = location.machines.exclude(id=machine_id).filter(
            map_position_x__isnull=False,
            map_position_y__isnull=False
        )
    
    # Get available trainers (staff members who can provide training)
    trainers = User.objects.filter(
        is_staff=True, 
        is_active=True
    ).order_by('first_name', 'last_name')
    
    context = {
        'machine': machine,
        'location': location,
        'has_floorplan': has_floorplan,
        'floorplan_url': floorplan_url,
        'other_machines': other_machines,
        'trainers': trainers,
        'today': date.today().isoformat(),
        'reservation_api_url': f'/reservations/api/machines/{machine_id}/reserve/',
        'availability_api_url': f'/reservations/api/machines/{machine_id}/availability/',
    }
    return render(request, 'machines/machine_detail.html', context)

@login_required
def machine_management_landing(request):
    """Landing page for machine management with two options"""
    # Get quick stats for the overview section
    total_machines = Machine.objects.count()
    # Since there's no status field, just count all machines as active
    active_machines = total_machines
    categories_count = Machine.objects.values('category').distinct().count()
    
    context = {
        'total_machines': total_machines,
        'active_machines': active_machines,
        'categories_count': categories_count,
    }
    
    return render(request, 'machines/machine_management_landing.html', context)



@user_passes_test(is_superuser)
def staff_machine_directory(request):
    """Staff-specific machine directory with all machines and advanced filtering"""
    from locations.models import Location
    
    # Get all machines (staff can see everything)
    machines = Machine.objects.all().prefetch_related('required_trainings').order_by('-created_at')
    
    # Get all locations for filter dropdown
    locations = Location.objects.all().order_by('building', 'name')
    
    context = {
        'machines': machines,
        'locations': locations,
    }
    
    return render(request, 'machines/staff_machine_directory.html', context)



@user_passes_test(is_superuser)
def edit_machine(request, machine_id):
    """Edit an existing machine"""
    from locations.models import Location
    
    machine = get_object_or_404(Machine, id=machine_id)
    
    if request.method == 'POST':
        # Handle the form submission
        machine.name = request.POST.get('name')
        machine.machine_name = request.POST.get('machine_name')
        machine.category = request.POST.get('category')
        machine.description = request.POST.get('description', '')
        machine.location = request.POST.get('location')
        machine.year_bought = request.POST.get('year_bought')
        machine.mac_address = request.POST.get('mac_address', '')
        
        # Handle training requirements
        machine.requires_level_1 = request.POST.get('requires_level_1') == 'on'
        machine.requires_level_2 = request.POST.get('requires_level_2') == 'on'
        machine.requires_level_3 = request.POST.get('requires_level_3') == 'on'
        
        # Handle image upload if provided
        if 'image' in request.FILES:
            machine.image = request.FILES['image']
        
        machine.save()
        
        messages.success(request, f'Machine "{machine.machine_name}" updated successfully!')
        return redirect('staff_machine_directory')
    
    # GET request - show the edit form
    locations = Location.objects.all()
    
    # Get all unique images grouped by category for image selection
    images_by_category = defaultdict(list)
    seen_images = defaultdict(set)
    
    all_machines_with_images = Machine.objects.filter(
        image__isnull=False
    ).exclude(
        image=''
    ).order_by('category', '-created_at')
    
    for m in all_machines_with_images:
        if m.image:
            image_name = m.image.name
            if image_name not in seen_images[m.category]:
                images_by_category[m.category].append({
                    'url': m.image.url,
                    'name': image_name,
                    'machine_example': f"{m.name} ({m.machine_name})"
                })
                seen_images[m.category].add(image_name)
    
    context = {
        'machine': machine,
        'locations': locations,
        'images_by_category': dict(images_by_category),
        'category_order': ['Laser', 'Vinyl', 'Woodworking', 'Textile', 'Metalworking', '3D Printing', 'Electronics'],
        'edit_mode': True,
    }
    
    return render(request, 'machines/edit_machine_form.html', context)


@user_passes_test(is_superuser)
def machine_detail_api(request, machine_id):
    """API endpoint to get comprehensive machine details for modal"""
    try:
        # Prefetch related objects for efficiency
        machine = Machine.objects.select_related('location').prefetch_related('required_trainings').get(id=machine_id)
        
        # Get training details
        trainings = []
        try:
            if machine.required_trainings.exists():
                trainings = [{'id': t.id, 'name': t.name} for t in machine.required_trainings.all()]
        except:
            pass
            
        # Add level-based training if no custom trainings
        if not trainings:
            if machine.requires_level_1:
                trainings.append({'name': 'Level 1 Training', 'type': 'level'})
            if machine.requires_level_2:
                trainings.append({'name': 'Level 2 Training', 'type': 'level'})
            if machine.requires_level_3:
                trainings.append({'name': 'Level 3 Training', 'type': 'level'})
        
        # Skip reservations for now since the table doesn't exist
        reservations_data = []
        
        # Get location details
        location_str = 'Not assigned'
        if machine.location:
            location_str = f"{machine.location.name}"
            if machine.location.building:
                location_str = f"{machine.location.building} - {machine.location.name}"
        
        data = {
            'id': machine.id,
            'name': machine.name,
            'machine_name': machine.machine_name,
            'category': machine.category,
            'description': machine.description or 'No description available',
            'location': location_str,
            'location_id': machine.location.id if machine.location else None,
            'year_bought': str(machine.year_bought) if machine.year_bought else 'N/A',
            'mac_address': machine.mac_address or 'Not connected',
            'image_url': machine.image.url if machine.image else None,
            'map_position_x': float(machine.map_position_x) if machine.map_position_x else None,
            'map_position_y': float(machine.map_position_y) if machine.map_position_y else None,
            'trainings': trainings,
            'reservations': reservations_data,
            'created_at': machine.created_at.strftime('%B %d, %Y at %I:%M %p'),
            'updated_at': machine.updated_at.strftime('%B %d, %Y at %I:%M %p'),
        }
        
        return JsonResponse(data)
        
    except Machine.DoesNotExist:
        return JsonResponse({'error': 'Machine not found'}, status=404)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in machine_detail_api: {e}")
        print(error_details)
        return JsonResponse({
            'error': str(e),
            'details': error_details if request.user.is_superuser else 'Server error'
        }, status=500)
    


    
"""
Training Management Views - Add these to your existing machines/views.py

These views handle training management for the makerspace.
"""

# ============================================================================
# TRAINING MANAGEMENT PAGE
# ============================================================================

@login_required
@user_passes_test(is_superuser)
def training_management(request):
    """Training management page"""
    return render(request, 'machines/training_management.html')


# ============================================================================
# TRAINING API ENDPOINTS
# ============================================================================

@login_required
@user_passes_test(is_superuser)
def api_get_trainings(request):
    """Get all trainings with their machine type assignments"""
    from .models import Training
    
    status_filter = request.GET.get('status', 'active')
    category_filter = request.GET.get('category', '')
    
    trainings = Training.objects.all()
    
    if status_filter and status_filter != 'all':
        trainings = trainings.filter(status=status_filter)
    
    if category_filter:
        trainings = trainings.filter(category=category_filter)
    
    trainings = trainings.prefetch_related('prerequisites')
    
    data = []
    for t in trainings:
        # Count user records if UserTrainingRecord model exists
        user_count = 0
        try:
            user_count = t.user_records.filter(status='completed').count()
        except:
            pass
        
        data.append({
            'id': t.id,
            'name': t.name,
            'description': t.description,
            'level': t.level,
            'level_display': t.level_display,
            'category': t.category,
            'machine_type_names': t.machine_type_names or [],
            'prerequisites': [
                {'id': p.id, 'name': p.name, 'level': p.level}
                for p in t.prerequisites.all()
            ],
            'duration_minutes': t.duration_minutes,
            'max_participants': t.max_participants,
            'materials_url': t.materials_url,
            'video_url': t.video_url,
            'status': t.status,
            'user_count': user_count,
            'created_at': t.created_at.isoformat(),
            'updated_at': t.updated_at.isoformat(),
        })
    
    return JsonResponse({'trainings': data})


@login_required
@user_passes_test(is_superuser)
def api_create_training(request):
    """Create a new training"""
    from .models import Training
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        name = data.get('name', '').strip()
        if not name:
            return JsonResponse({'success': False, 'error': 'Training name is required'})
        
        category = data.get('category', '').strip()
        if not category:
            return JsonResponse({'success': False, 'error': 'Category is required'})
        
        level = data.get('level', 1)
        if level not in [1, 2, 3]:
            return JsonResponse({'success': False, 'error': 'Level must be 1, 2, or 3'})
        
        # Create training
        training = Training.objects.create(
            name=name,
            description=data.get('description', ''),
            level=level,
            category=category,
            duration_minutes=data.get('duration_minutes', 60),
            max_participants=data.get('max_participants', 4),
            materials_url=data.get('materials_url', ''),
            video_url=data.get('video_url', ''),
            status=data.get('status', 'active'),
            machine_type_names=data.get('machine_type_names', []),
            created_by=request.user,
        )
        
        # Assign prerequisites
        prerequisite_ids = data.get('prerequisite_ids', [])
        if prerequisite_ids:
            prerequisites = Training.objects.filter(id__in=prerequisite_ids)
            training.prerequisites.set(prerequisites)
        
        return JsonResponse({
            'success': True, 
            'training_id': training.id,
            'message': f'Training "{name}" created successfully'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_superuser)
def api_update_training(request, training_id):
    """Update an existing training"""
    from .models import Training
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        training = get_object_or_404(Training, id=training_id)
        
        # Update fields
        if 'name' in data:
            training.name = data['name'].strip()
        if 'description' in data:
            training.description = data['description']
        if 'level' in data:
            if data['level'] in [1, 2, 3]:
                training.level = data['level']
        if 'category' in data:
            training.category = data['category'].strip()
        if 'duration_minutes' in data:
            training.duration_minutes = data['duration_minutes']
        if 'max_participants' in data:
            training.max_participants = data['max_participants']
        if 'materials_url' in data:
            training.materials_url = data['materials_url']
        if 'video_url' in data:
            training.video_url = data['video_url']
        if 'status' in data:
            training.status = data['status']
        if 'machine_type_names' in data:
            training.machine_type_names = data['machine_type_names']
        
        training.save()
        
        # Update prerequisites
        if 'prerequisite_ids' in data:
            # Prevent self-reference
            prereq_ids = [pid for pid in data['prerequisite_ids'] if pid != training_id]
            prerequisites = Training.objects.filter(id__in=prereq_ids)
            training.prerequisites.set(prerequisites)
        
        return JsonResponse({'success': True, 'message': 'Training updated successfully'})
        
    except Training.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Training not found'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_superuser)
def api_archive_training(request, training_id):
    """Archive a training (soft delete)"""
    from .models import Training
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        training = get_object_or_404(Training, id=training_id)
        training.status = 'archived'
        training.save()
        
        return JsonResponse({'success': True, 'message': 'Training archived successfully'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_superuser)
def api_delete_training(request, training_id):
    """Permanently delete a training"""
    from .models import Training
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        training = get_object_or_404(Training, id=training_id)
        name = training.name
        training.delete()
        
        return JsonResponse({'success': True, 'message': f'Training "{name}" deleted permanently'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_superuser)
def api_bulk_training_action(request):
    """Bulk archive, restore, or delete trainings"""
    from .models import Training
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        training_ids = data.get('training_ids', [])
        action = data.get('action', '')
        
        if not training_ids:
            return JsonResponse({'success': False, 'error': 'No trainings selected'})
        
        trainings = Training.objects.filter(id__in=training_ids)
        count = trainings.count()
        
        if action == 'archive':
            trainings.update(status='archived')
            return JsonResponse({'success': True, 'message': f'Archived {count} training(s)'})
        elif action == 'restore':
            trainings.update(status='active')
            return JsonResponse({'success': True, 'message': f'Restored {count} training(s)'})
        elif action == 'delete':
            trainings.delete()
            return JsonResponse({'success': True, 'message': f'Deleted {count} training(s)'})
        elif action == 'activate':
            trainings.update(status='active')
            return JsonResponse({'success': True, 'message': f'Activated {count} training(s)'})
        else:
            return JsonResponse({'success': False, 'error': 'Invalid action'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ============================================================================
# EXISTING MACHINE TYPES API (reads from Machine.machine_name)
# ============================================================================

@login_required
def api_get_existing_machine_types(request):
    """Get unique machine types (machine_name) from existing machines, grouped by category"""
    from .models import Machine, MachineCategory
    from django.db.models import Count
    
    # Get unique machine_name values grouped by category with counts
    machine_types = Machine.objects.values('category', 'machine_name').annotate(
        count=Count('id')
    ).order_by('category', 'machine_name')
    
    # Get category info for icons/colors
    categories = MachineCategory.objects.filter(is_active=True)
    category_info = {c.name: {'icon': c.icon, 'color': c.color} for c in categories}
    
    # Group by category
    by_category = {}
    all_types = []
    
    for mt in machine_types:
        cat = mt['category']
        name = mt['machine_name']
        count = mt['count']
        
        if cat not in by_category:
            by_category[cat] = []
        
        type_data = {'name': name, 'category': cat, 'count': count}
        by_category[cat].append(type_data)
        all_types.append(type_data)
    
    return JsonResponse({
        'machine_types': all_types,
        'by_category': by_category,
        'category_info': category_info,
    })



# ============================================================================
# CATEGORY MANAGEMENT PAGE
# ============================================================================

@login_required
@user_passes_test(is_superuser)
def manage_categories(request):
    """Category management page"""
    return render(request, 'machines/manage_categories.html')


# ============================================================================
# CATEGORY API ENDPOINTS
# ============================================================================

@login_required
def api_get_categories(request):
    """Get all categories"""
    from .models import MachineCategory
    
    include_inactive = request.GET.get('include_inactive', 'false') == 'true'
    
    categories = MachineCategory.objects.all().order_by('display_order', 'name')
    
    data = []
    for cat in categories:
        if not include_inactive and not cat.is_active:
            continue
        data.append({
            'id': cat.id,
            'name': cat.name,
            'description': cat.description,
            'icon': cat.icon,
            'color': cat.color,
            'display_order': cat.display_order,
            'is_active': cat.is_active,
            'machine_count': cat.machine_count,
            'created_at': cat.created_at.isoformat() if cat.created_at else None,
        })
    
    return JsonResponse({'categories': data})


@login_required
@user_passes_test(is_superuser)
def api_create_category(request):
    """Create a new category"""
    from .models import MachineCategory
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        name = data.get('name', '').strip()
        if not name:
            return JsonResponse({'success': False, 'error': 'Category name is required'})
        
        # Check for duplicates
        if MachineCategory.objects.filter(name__iexact=name).exists():
            return JsonResponse({'success': False, 'error': f'Category "{name}" already exists'})
        
        category = MachineCategory.objects.create(
            name=name,
            description=data.get('description', ''),
            icon=data.get('icon', '🔧'),
            color=data.get('color', '#293242'),
            display_order=data.get('display_order', 0),
            is_active=data.get('is_active', True),
        )
        
        return JsonResponse({
            'success': True,
            'category_id': category.id,
            'message': f'Category "{name}" created successfully'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_superuser)
def api_update_category(request, category_id):
    """Update an existing category"""
    from .models import MachineCategory
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        category = get_object_or_404(MachineCategory, id=category_id)
        
        # Check for duplicate name
        new_name = data.get('name', '').strip()
        if new_name and new_name.lower() != category.name.lower():
            if MachineCategory.objects.filter(name__iexact=new_name).exclude(id=category_id).exists():
                return JsonResponse({'success': False, 'error': f'Category "{new_name}" already exists'})
        
        # Update fields
        if 'name' in data:
            category.name = data['name'].strip()
        if 'description' in data:
            category.description = data['description']
        if 'icon' in data:
            category.icon = data['icon']
        if 'color' in data:
            category.color = data['color']
        if 'display_order' in data:
            category.display_order = data['display_order']
        if 'is_active' in data:
            category.is_active = data['is_active']
        
        category.save()
        
        return JsonResponse({'success': True, 'message': 'Category updated successfully'})
        
    except MachineCategory.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Category not found'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_superuser)
def api_delete_category(request, category_id):
    """Delete a category"""
    from .models import MachineCategory, Machine
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        category = get_object_or_404(MachineCategory, id=category_id)
        
        # Check if any machines are using this category (via category_fk)
        machine_count = Machine.objects.filter(category_fk=category).count()
        if machine_count > 0:
            return JsonResponse({
                'success': False,
                'error': f'Cannot delete: {machine_count} machine(s) are using this category. Reassign them first.'
            })
        
        name = category.name
        category.delete()
        
        return JsonResponse({'success': True, 'message': f'Category "{name}" deleted successfully'})
        
    except MachineCategory.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Category not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ============================================================================
# TRAINING MANAGEMENT PAGE
# ============================================================================

@login_required
@user_passes_test(is_superuser)
def training_management(request):
    """Training management page"""
    return render(request, 'machines/training_management.html')


# ============================================================================
# TRAINING API ENDPOINTS
# ============================================================================

@login_required
@user_passes_test(is_superuser)
def api_get_trainings(request):
    """Get all trainings with their machine type assignments"""
    from .models import Training
    
    status_filter = request.GET.get('status', 'active')
    category_filter = request.GET.get('category', '')
    
    trainings = Training.objects.all()
    
    if status_filter and status_filter != 'all':
        trainings = trainings.filter(status=status_filter)
    
    if category_filter:
        trainings = trainings.filter(category=category_filter)
    
    trainings = trainings.prefetch_related('prerequisites')
    
    data = []
    for t in trainings:
        # Count user records if UserTrainingRecord model exists
        user_count = 0
        try:
            user_count = t.user_records.filter(status='completed').count()
        except:
            pass
        
        data.append({
            'id': t.id,
            'name': t.name,
            'description': t.description,
            'level': t.level,
            'level_display': t.level_display,
            'category': t.category,
            'machine_type_names': t.machine_type_names or [],
            'prerequisites': [
                {'id': p.id, 'name': p.name, 'level': p.level}
                for p in t.prerequisites.all()
            ],
            'duration_minutes': t.duration_minutes,
            'max_participants': t.max_participants,
            'materials_url': t.materials_url,
            'video_url': t.video_url,
            'status': t.status,
            'user_count': user_count,
            'created_at': t.created_at.isoformat(),
            'updated_at': t.updated_at.isoformat(),
        })
    
    return JsonResponse({'trainings': data})


@login_required
@user_passes_test(is_superuser)
def api_create_training(request):
    """Create a new training"""
    from .models import Training
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        name = data.get('name', '').strip()
        if not name:
            return JsonResponse({'success': False, 'error': 'Training name is required'})
        
        category = data.get('category', '').strip()
        if not category:
            return JsonResponse({'success': False, 'error': 'Category is required'})
        
        level = data.get('level', 1)
        if level not in [1, 2, 3]:
            return JsonResponse({'success': False, 'error': 'Level must be 1, 2, or 3'})
        
        # Create training
        training = Training.objects.create(
            name=name,
            description=data.get('description', ''),
            level=level,
            category=category,
            duration_minutes=data.get('duration_minutes', 60),
            max_participants=data.get('max_participants', 4),
            materials_url=data.get('materials_url', ''),
            video_url=data.get('video_url', ''),
            status=data.get('status', 'active'),
            machine_type_names=data.get('machine_type_names', []),
            created_by=request.user,
        )
        
        # Assign prerequisites
        prerequisite_ids = data.get('prerequisite_ids', [])
        if prerequisite_ids:
            prerequisites = Training.objects.filter(id__in=prerequisite_ids)
            training.prerequisites.set(prerequisites)
        
        return JsonResponse({
            'success': True, 
            'training_id': training.id,
            'message': f'Training "{name}" created successfully'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_superuser)
def api_update_training(request, training_id):
    """Update an existing training"""
    from .models import Training
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        training = get_object_or_404(Training, id=training_id)
        
        # Update fields
        if 'name' in data:
            training.name = data['name'].strip()
        if 'description' in data:
            training.description = data['description']
        if 'level' in data:
            if data['level'] in [1, 2, 3]:
                training.level = data['level']
        if 'category' in data:
            training.category = data['category'].strip()
        if 'duration_minutes' in data:
            training.duration_minutes = data['duration_minutes']
        if 'max_participants' in data:
            training.max_participants = data['max_participants']
        if 'materials_url' in data:
            training.materials_url = data['materials_url']
        if 'video_url' in data:
            training.video_url = data['video_url']
        if 'status' in data:
            training.status = data['status']
        if 'machine_type_names' in data:
            training.machine_type_names = data['machine_type_names']
        
        training.save()
        
        # Update prerequisites
        if 'prerequisite_ids' in data:
            # Prevent self-reference
            prereq_ids = [pid for pid in data['prerequisite_ids'] if pid != training_id]
            prerequisites = Training.objects.filter(id__in=prereq_ids)
            training.prerequisites.set(prerequisites)
        
        return JsonResponse({'success': True, 'message': 'Training updated successfully'})
        
    except Training.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Training not found'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_superuser)
def api_archive_training(request, training_id):
    """Archive a training (soft delete)"""
    from .models import Training
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        training = get_object_or_404(Training, id=training_id)
        training.status = 'archived'
        training.save()
        
        return JsonResponse({'success': True, 'message': 'Training archived successfully'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_superuser)
def api_delete_training(request, training_id):
    """Permanently delete a training"""
    from .models import Training
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        training = get_object_or_404(Training, id=training_id)
        name = training.name
        training.delete()
        
        return JsonResponse({'success': True, 'message': f'Training "{name}" deleted permanently'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_superuser)
def api_bulk_training_action(request):
    """Bulk archive, restore, or delete trainings"""
    from .models import Training
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        training_ids = data.get('training_ids', [])
        action = data.get('action', '')
        
        if not training_ids:
            return JsonResponse({'success': False, 'error': 'No trainings selected'})
        
        trainings = Training.objects.filter(id__in=training_ids)
        count = trainings.count()
        
        if action == 'archive':
            trainings.update(status='archived')
            return JsonResponse({'success': True, 'message': f'Archived {count} training(s)'})
        elif action == 'restore':
            trainings.update(status='active')
            return JsonResponse({'success': True, 'message': f'Restored {count} training(s)'})
        elif action == 'delete':
            trainings.delete()
            return JsonResponse({'success': True, 'message': f'Deleted {count} training(s)'})
        elif action == 'activate':
            trainings.update(status='active')
            return JsonResponse({'success': True, 'message': f'Activated {count} training(s)'})
        else:
            return JsonResponse({'success': False, 'error': 'Invalid action'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ============================================================================
# EXISTING MACHINE TYPES API (reads from Machine.machine_name)
# ============================================================================

@login_required
def api_get_existing_machine_types(request):
    """Get unique machine types (machine_name) from existing machines, grouped by category"""
    from .models import Machine, MachineCategory
    from django.db.models import Count
    
    # Get unique machine_name values grouped by category with counts
    machine_types = Machine.objects.values('category', 'machine_name').annotate(
        count=Count('id')
    ).order_by('category', 'machine_name')
    
    # Get category info for icons/colors
    categories = MachineCategory.objects.filter(is_active=True)
    category_info = {c.name: {'icon': c.icon, 'color': c.color} for c in categories}
    
    # Group by category
    by_category = {}
    all_types = []
    
    for mt in machine_types:
        cat = mt['category']
        name = mt['machine_name']
        count = mt['count']
        
        if cat not in by_category:
            by_category[cat] = []
        
        type_data = {'name': name, 'category': cat, 'count': count}
        by_category[cat].append(type_data)
        all_types.append(type_data)
    
    return JsonResponse({
        'machine_types': all_types,
        'by_category': by_category,
        'category_info': category_info,
    })
