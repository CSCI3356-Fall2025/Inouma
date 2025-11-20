import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from .models import Machine
from collections import defaultdict
import os
from django.conf import settings
from .utils import convert_heic_to_jpg


def is_superuser(user):
    return user.is_superuser

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
            'x': m.map_position_x,
            'y': m.map_position_y
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
        'locations_data': locations_data,  # This includes all the detailed info
        'images_by_category': dict(images_by_category),
        'category_order': category_order,
    }
    return render(request, 'machines/add_machine_form.html', context)


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
            location=request.POST.get('location'),
            description=request.POST.get('description', ''),
            mac_address=request.POST.get('mac_address', ''),
            year_bought=request.POST.get('year_bought') or None,
            requires_level_1=request.POST.get('requires_level_1') == 'on',
            requires_level_2=request.POST.get('requires_level_2') == 'on',
            requires_level_3=request.POST.get('requires_level_3') == 'on',
            # Add map position coordinates
            map_position_x=request.POST.get('map_position_x') or None,
            map_position_y=request.POST.get('map_position_y') or None,
        )
        
        
        # Assign image if provided
        if machine_image:
            machine.image = machine_image
        
        machine.save()
        messages.success(request, f'Machine "{machine.name}" added successfully!')
        return redirect('staff_dashboard')
    return redirect('staff_dashboard')


@login_required
def remove_machine(request, machine_id):
    if request.method == 'POST':
        machine = get_object_or_404(Machine, id=machine_id)
        machine_name = machine.name
        
        # Note: We DON'T delete the image file since other machines might be using it
        machine.delete()
        messages.success(request, f'Machine "{machine_name}" removed successfully!')
    return redirect('staff_dashboard')

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
    """API endpoint to get search suggestions for both machine types and identifiers"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 1:
        return JsonResponse({'suggestions': []})
    
    # Get machine types that match (already distinct from the query)
    machine_types = Machine.objects.filter(
        machine_name__icontains=query
    ).values_list('machine_name', flat=True).distinct()
    
    # Get machine identifiers that match (already distinct from the query)
    machine_names = Machine.objects.filter(
        name__icontains=query
    ).values_list('name', flat=True).distinct()
    
    # Combine with labels - return both display and value
    suggestions = []
    seen = set()  # Track what we've already added
    
    for mt in machine_types[:5]:
        if mt.lower() not in seen:
            suggestions.append({
                'display': f"{mt} (Machine Type)",
                'value': mt
            })
            seen.add(mt.lower())
    
    for mn in machine_names[:5]:
        if mn.lower() not in seen:
            suggestions.append({
                'display': f"{mn} (Machine Name)",
                'value': mn
            })
            seen.add(mn.lower())
    
    return JsonResponse({'suggestions': suggestions})





