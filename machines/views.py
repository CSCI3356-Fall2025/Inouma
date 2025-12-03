from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import models
from django.conf import settings

from datetime import date

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse

from .models import Machine
from locations.models import Location

from .models import Machine, TrainingType, MachineCategory, Training
from locations.models import Location
from collections import defaultdict
import json
import os


def is_superuser(user):
    return user.is_superuser


# ============================================================================
# STAFF DASHBOARD
# ============================================================================

@login_required
def staff_dashboard(request):
    """Main staff dashboard"""
    machines = Machine.objects.all()
    machines_by_category = defaultdict(list)
    
    for machine in machines:
        machines_by_category[machine.category].append(machine)
    
    category_order = ['Laser', 'Vinyl', 'Woodworking', 'Textile', 'Metalworking', '3D Printing', 'Electronics']
    machines_by_category = {cat: machines_by_category[cat] for cat in category_order if cat in machines_by_category}
    
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
    
    context = {
        'machines_by_category': machines_by_category,
        'images_by_category': dict(images_by_category),
        'category_order': category_order,
    }
    return render(request, 'staff_dashboard.html', context)


# ============================================================================
# MACHINE MANAGEMENT
# ============================================================================

@login_required
def machine_management_landing(request):
    """Landing page for machine management with two options"""
    total_machines = Machine.objects.count()
    active_machines = total_machines
    categories_count = Machine.objects.values('category').distinct().count()
    
    context = {
        'total_machines': total_machines,
        'active_machines': active_machines,
        'categories_count': categories_count,
    }
    
    return render(request, 'machines/machine_management_landing.html', context)


@login_required
@user_passes_test(is_superuser)
@require_http_methods(["GET", "POST"])
def add_machine(request):
    """Handle adding a new machine - renders add_machine_form.html"""
    
    if request.method == 'POST':
        try:
            # Get form data
            machine_name = request.POST.get('machine_name', '').strip()  # Machine TYPE
            name = request.POST.get('name', '').strip()  # Specific identifier
            category_id = request.POST.get('category')
            location_id = request.POST.get('location')
            description = request.POST.get('description', '').strip()
            
            # Optional fields (none of these are required)
            # Use empty string for text fields to avoid NOT NULL constraints
            manufacturer = request.POST.get('manufacturer', '').strip()
            model_number = request.POST.get('model_number', '').strip()
            documentation_url = request.POST.get('documentation_url', '').strip()
            year_bought = request.POST.get('year_bought') or None
            mac_address = request.POST.get('mac_address', '').strip()
            
            # Map coordinates
            map_position_x = request.POST.get('map_position_x')
            map_position_y = request.POST.get('map_position_y')
            
            # Reservation setting
            is_reservable = request.POST.get('is_reservable') == 'on'
            
            # Required training
            required_training_id = request.POST.get('required_training')
            
            # Validate required fields
            if not machine_name:
                raise ValueError("Machine type/model is required")
            if not name:
                raise ValueError("Machine name/identifier is required")
            if not category_id:
                raise ValueError("Category is required")
            if not location_id:
                raise ValueError("Location is required")
            
            # Get related objects
            category = MachineCategory.objects.get(id=category_id)
            location = Location.objects.get(id=location_id)
            
            # Get training if specified
            required_training = None
            if required_training_id:
                required_training = Training.objects.get(id=required_training_id)
            
            # Handle image
            image_choice = request.POST.get('image_choice', 'default')
            image = None
            
            if image_choice == 'existing':
                existing_image = request.POST.get('existing_image')
                if existing_image:
                    image = f'machine_images/{existing_image}'
            elif image_choice == 'upload':
                if 'custom_image' in request.FILES:
                    image = request.FILES['custom_image']
            
            # Create the machine
            machine = Machine(
                machine_name=machine_name,
                name=name,
                category=category.name,  # Store category name string
                location=location,
                description=description or '',
                year_bought=int(year_bought) if year_bought else None,
                mac_address=mac_address or '',
                manufacturer=manufacturer or '',
                model_number=model_number or '',
                documentation_url=documentation_url or '',
            )
            
            # Set additional optional fields if they exist on the model
            if hasattr(machine, 'is_reservable'):
                machine.is_reservable = is_reservable
            if hasattr(machine, 'required_training'):
                machine.required_training = required_training
            if hasattr(machine, 'category_fk'):
                machine.category_fk = category
            
            # Set map position if provided
            if map_position_x and map_position_y:
                machine.map_position_x = float(map_position_x)
                machine.map_position_y = float(map_position_y)
            
            # Handle image
            if image:
                machine.image = image
            
            machine.save()
            
            # Check if AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Machine "{name}" added successfully!',
                    'machine_id': machine.id,
                    'machine_name': name
                })
            else:
                messages.success(request, f'Machine "{name}" added successfully!')
                return redirect('machine_management')
                
        except MachineCategory.DoesNotExist:
            error = "Invalid category selected"
        except Location.DoesNotExist:
            error = "Invalid location selected"
        except Training.DoesNotExist:
            error = "Invalid training selected"
        except ValueError as e:
            error = str(e)
        except Exception as e:
            import traceback
            traceback.print_exc()
            error = f"Error adding machine: {str(e)}"
        
        # Handle errors
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error}, status=400)
        else:
            messages.error(request, error)
    
    # GET request - render form
    locations = Location.objects.all().order_by('name')
    
    # Prepare locations data for JavaScript
    locations_data = []
    for loc in locations:
        # Get machines at this location
        machines_at_loc = Machine.objects.filter(location=loc)
        
        loc_data = {
            'id': loc.id,
            'name': loc.name,
            'building': getattr(loc, 'building', ''),
            'floor': getattr(loc, 'floor', ''),
            'num_stations': getattr(loc, 'num_stations', 0),
            'capacity': getattr(loc, 'capacity', 0),
            'machine_types': list(machines_at_loc.values_list('machine_name', flat=True).distinct()),
            'has_floorplan': bool(getattr(loc, 'floorplan_image', None)),
            'floorplan_url': loc.floorplan_image.url if getattr(loc, 'floorplan_image', None) else None,
            'machines': [
                {
                    'name': m.name,
                    'machine_name': m.machine_name,
                    'x': m.map_position_x,
                    'y': m.map_position_y
                }
                for m in machines_at_loc.filter(map_position_x__isnull=False, map_position_y__isnull=False)
            ]
        }
        locations_data.append(loc_data)
    
    # Get existing machine images grouped by category
    images_by_category = defaultdict(list)
    seen_images = defaultdict(set)
    
    all_machines_with_images = Machine.objects.filter(
        image__isnull=False
    ).exclude(image='').order_by('category', '-created_at')
    
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
        'locations_data_json': json.dumps(locations_data),
        'images_by_category': dict(images_by_category),
        'category_order': category_order,
    }
    
    return render(request, 'machines/add_machine_form.html', context)


# Keep machine_management as an alias for backwards compatibility with urls.py
machine_management = add_machine


@login_required
@user_passes_test(is_superuser)
def edit_machine(request, machine_id):
    """Edit an existing machine"""
    machine = get_object_or_404(Machine, id=machine_id)
    
    if request.method == 'POST':
        machine.name = request.POST.get('name')
        machine.machine_name = request.POST.get('machine_name')
        machine.category = request.POST.get('category')
        machine.description = request.POST.get('description', '')
        
        # Handle location
        location_id = request.POST.get('location')
        if location_id:
            try:
                machine.location = Location.objects.get(id=location_id)
            except Location.DoesNotExist:
                pass
        
        machine.year_bought = request.POST.get('year_bought') or None
        machine.mac_address = request.POST.get('mac_address', '')
        
        # Handle reservation setting if field exists
        if hasattr(machine, 'is_reservable'):
            machine.is_reservable = request.POST.get('is_reservable') == 'on'
        
        # Handle required training if field exists
        if hasattr(machine, 'required_training'):
            required_training_id = request.POST.get('required_training')
            if required_training_id:
                try:
                    machine.required_training = Training.objects.get(id=required_training_id)
                except Training.DoesNotExist:
                    machine.required_training = None
            else:
                machine.required_training = None
        
        # Handle legacy training levels if they exist
        if hasattr(machine, 'requires_level_1'):
            machine.requires_level_1 = request.POST.get('requires_level_1') == 'on'
        if hasattr(machine, 'requires_level_2'):
            machine.requires_level_2 = request.POST.get('requires_level_2') == 'on'
        if hasattr(machine, 'requires_level_3'):
            machine.requires_level_3 = request.POST.get('requires_level_3') == 'on'
        
        # Handle image upload if provided
        if 'image' in request.FILES:
            machine.image = request.FILES['image']
        
        machine.save()
        
        messages.success(request, f'Machine "{machine.machine_name}" updated successfully!')
        return redirect('staff_machine_directory')
    
    # GET request - show the edit form
    locations = Location.objects.all()
    trainings = Training.objects.filter(status='active').order_by('category', 'name')
    
    # Get all unique images grouped by category
    images_by_category = defaultdict(list)
    seen_images = defaultdict(set)
    
    all_machines_with_images = Machine.objects.filter(
        image__isnull=False
    ).exclude(image='').order_by('category', '-created_at')
    
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
        'trainings': trainings,
        'images_by_category': dict(images_by_category),
        'category_order': ['Laser', 'Vinyl', 'Woodworking', 'Textile', 'Metalworking', '3D Printing', 'Electronics'],
        'edit_mode': True,
    }
    
    return render(request, 'machines/edit_machine_form.html', context)


@login_required
@user_passes_test(is_superuser)
def remove_machine(request, machine_id):
    """Delete a machine from the database"""
    if request.method == 'POST':
        try:
            machine = get_object_or_404(Machine, id=machine_id)
            machine_name = machine.machine_name
            
            # Clear many-to-many relationships first if they exist
            if hasattr(machine, 'required_trainings'):
                machine.required_trainings.clear()
            
            machine.delete()
            
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
            traceback.print_exc()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f'Error deleting machine: {error_msg}'
                }, status=500)
            
            messages.error(request, f'Error deleting machine: {error_msg}')
            return redirect('staff_machine_directory')
    
    return redirect('staff_machine_directory')


@login_required
@user_passes_test(is_superuser)
def staff_machine_directory(request):
    """Staff-specific machine directory with all machines and advanced filtering"""
    machines = Machine.objects.all().order_by('-created_at')
    
    # Try to prefetch related trainings if the relationship exists
    try:
        machines = machines.prefetch_related('required_trainings')
    except:
        pass
    
    locations = Location.objects.all().order_by('building', 'name')
    
    context = {
        'machines': machines,
        'locations': locations,
    }
    
    return render(request, 'machines/staff_machine_directory.html', context)


@login_required
@user_passes_test(is_superuser)
def machine_detail_api(request, machine_id):
    """API endpoint to get comprehensive machine details for modal"""
    try:
        machine = Machine.objects.get(id=machine_id)
        
        # Try to get related objects
        try:
            machine = Machine.objects.select_related('location').get(id=machine_id)
        except:
            pass
        
        # Get training details
        trainings = []
        
        # Check for required_training (single FK)
        if hasattr(machine, 'required_training') and machine.required_training:
            trainings.append({
                'id': machine.required_training.id,
                'name': machine.required_training.name
            })
        
        # Check for required_trainings (M2M)
        if hasattr(machine, 'required_trainings'):
            try:
                if machine.required_trainings.exists():
                    trainings = [{'id': t.id, 'name': t.name} for t in machine.required_trainings.all()]
            except:
                pass
        
        # Add level-based training if no custom trainings
        if not trainings:
            if getattr(machine, 'requires_level_1', False):
                trainings.append({'name': 'Level 1 Training', 'type': 'level'})
            if getattr(machine, 'requires_level_2', False):
                trainings.append({'name': 'Level 2 Training', 'type': 'level'})
            if getattr(machine, 'requires_level_3', False):
                trainings.append({'name': 'Level 3 Training', 'type': 'level'})
        
        # Get location details
        location_str = 'Not assigned'
        location_id = None
        if machine.location:
            if hasattr(machine.location, 'name'):
                location_str = machine.location.name
                location_id = machine.location.id
                if hasattr(machine.location, 'building') and machine.location.building:
                    location_str = f"{machine.location.building} - {machine.location.name}"
            else:
                location_str = str(machine.location)
        
        data = {
            'id': machine.id,
            'name': machine.name,
            'machine_name': machine.machine_name,
            'category': machine.category,
            'description': machine.description or 'No description available',
            'location': location_str,
            'location_id': location_id,
            'year_bought': str(machine.year_bought) if machine.year_bought else 'N/A',
            'mac_address': machine.mac_address or 'Not connected',
            'image_url': machine.image.url if machine.image else None,
            'map_position_x': float(machine.map_position_x) if machine.map_position_x else None,
            'map_position_y': float(machine.map_position_y) if machine.map_position_y else None,
            'is_reservable': getattr(machine, 'is_reservable', True),
            'trainings': trainings,
            'created_at': machine.created_at.strftime('%B %d, %Y at %I:%M %p'),
            'updated_at': machine.updated_at.strftime('%B %d, %Y at %I:%M %p'),
        }
        
        return JsonResponse(data)
        
    except Machine.DoesNotExist:
        return JsonResponse({'error': 'Machine not found'}, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# MACHINE DIRECTORY (User-facing)
# ============================================================================

@login_required
def machine_directory(request):
    """Display category overview - Level 1"""
    categories = Machine.objects.values('category').annotate(
        count=models.Count('id')
    ).order_by('category')
    
    category_order = ['Laser', 'Vinyl', 'Woodworking', 'Textile', 'Metalworking', '3D Printing', 'Electronics']
    
    category_data = []
    for cat in category_order:
        cat_info = next((c for c in categories if c['category'] == cat), None)
        if cat_info:
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
    machine_types = Machine.objects.filter(category=category).values('machine_name').annotate(
        count=models.Count('id')
    ).order_by('machine_name')
    
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
    """Display full machine details with floorplan and reservation capabilities - Level 4"""
    from django.contrib.auth import get_user_model
    from datetime import date
    
    User = get_user_model()
    machine = get_object_or_404(Machine, id=machine_id)
    
    location = machine.location
    has_floorplan = False
    floorplan_url = None
    
    if location and hasattr(location, 'floorplan_image'):
        has_floorplan = bool(location.floorplan_image)
        floorplan_url = location.floorplan_image.url if has_floorplan else None
    
    other_machines = []
    if location and hasattr(location, 'machines'):
        other_machines = location.machines.exclude(id=machine_id).filter(
            map_position_x__isnull=False,
            map_position_y__isnull=False
        )
    
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
@require_http_methods(["POST"])
def report_broken(request, machine_id):
    """Allow a user to report a machine as broken. Marks the machine status and redirects back."""
    try:
        machine = get_object_or_404(Machine, id=machine_id)

        # Update status if not already marked
        if getattr(machine, 'status', 'active') != 'broken':
            machine.status = 'broken'
            machine.save()
            messages.success(request, f'Machine "{machine.name}" reported as broken. Staff will be notified.')
        else:
            messages.info(request, f'Machine "{machine.name}" is already marked as broken.')

    except Exception as e:
        import traceback
        traceback.print_exc()
        messages.error(request, f'Error reporting machine: {e}')

    # Redirect back to the referring page if available, otherwise to the machine directory
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('machine_directory')


# ============================================================================
# MACHINE SUGGESTION APIs
# ============================================================================

@login_required
def get_machine_suggestions(request):
    """API endpoint to get machine type suggestions for autocomplete"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 1:
        return JsonResponse({'suggestions': []})
    
    machines = Machine.objects.filter(
        machine_name__icontains=query
    ).values_list('machine_name', flat=True)
    
    seen = set()
    unique_machines = []
    for machine in machines:
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
    
    duplicate = Machine.objects.filter(name__iexact=name, machine_name__iexact=machine_name).first()
    
    if duplicate:
        location_str = ''
        if duplicate.location:
            location_str = str(duplicate.location.name) if hasattr(duplicate.location, 'name') else str(duplicate.location)
        
        return JsonResponse({
            'duplicate': True,
            'machine_name': duplicate.machine_name,
            'name': duplicate.name,
            'location': location_str,
            'category': duplicate.category
        })
    
    return JsonResponse({'duplicate': False})


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
                suggestions.append({'text': machine_type, 'type': 'Machine Type'})
                seen.add(machine_type.lower())
        
        # Search machine names
        machine_names = Machine.objects.filter(
            name__icontains=query
        ).values_list('name', flat=True).distinct()[:5]
        
        for name in machine_names:
            if name and name.lower() not in seen:
                suggestions.append({'text': name, 'type': 'Machine ID'})
                seen.add(name.lower())
        
        # Search categories
        categories = Machine.objects.filter(
            category__icontains=query
        ).values_list('category', flat=True).distinct()[:3]
        
        for category in categories:
            if category and category.lower() not in seen:
                suggestions.append({'text': category, 'type': 'Category'})
                seen.add(category.lower())
        
        # Search locations
        location_objs = Location.objects.filter(name__icontains=query).distinct()[:3]
        
        for loc in location_objs:
            loc_text = f"{loc.building} - {loc.name}" if getattr(loc, 'building', None) else loc.name
            if loc_text.lower() not in seen:
                suggestions.append({'text': loc_text, 'type': 'Location'})
                seen.add(loc_text.lower())
    
    except Exception as e:
        print(f"Error in search suggestions: {e}")
        return JsonResponse({'suggestions': []})
    
    return JsonResponse({'suggestions': suggestions[:10]})


# ============================================================================
# CATEGORY MANAGEMENT
# ============================================================================

@login_required
@user_passes_test(is_superuser)
def manage_categories(request):
    """Category management page"""
    return render(request, 'machines/manage_categories.html')


@login_required
def api_get_categories(request):
    """Get all categories"""
    include_inactive = request.GET.get('include_inactive', 'false') == 'true'
    
    categories = MachineCategory.objects.all().order_by('display_order', 'name')
    
    data = []
    for cat in categories:
        if not include_inactive and not cat.is_active:
            continue
        data.append({
            'id': cat.id,
            'name': cat.name,
            'description': getattr(cat, 'description', ''),
            'icon': getattr(cat, 'icon', '🔧'),
            'color': getattr(cat, 'color', '#293242'),
            'display_order': getattr(cat, 'display_order', 0),
            'is_active': cat.is_active,
            'machine_count': getattr(cat, 'machine_count', 0),
            'created_at': cat.created_at.isoformat() if hasattr(cat, 'created_at') and cat.created_at else None,
        })
    
    return JsonResponse({'categories': data})


@login_required
@user_passes_test(is_superuser)
def api_create_category(request):
    """Create a new category"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        name = data.get('name', '').strip()
        if not name:
            return JsonResponse({'success': False, 'error': 'Category name is required'})
        
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
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        category = get_object_or_404(MachineCategory, id=category_id)
        
        new_name = data.get('name', '').strip()
        if new_name and new_name.lower() != category.name.lower():
            if MachineCategory.objects.filter(name__iexact=new_name).exclude(id=category_id).exists():
                return JsonResponse({'success': False, 'error': f'Category "{new_name}" already exists'})
        
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
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        category = get_object_or_404(MachineCategory, id=category_id)
        
        # Check if any machines are using this category
        machine_count = Machine.objects.filter(category=category.name).count()
        if hasattr(Machine, 'category_fk'):
            machine_count = max(machine_count, Machine.objects.filter(category_fk=category).count())
        
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
# TRAINING MANAGEMENT
# ============================================================================

@login_required
@user_passes_test(is_superuser)
def training_management(request):
    """Training management page"""
    return render(request, 'machines/training_management.html')


@login_required
def api_get_trainings(request):
    """Get all trainings with their machine type assignments"""
    status_filter = request.GET.get('status', 'active')
    category_filter = request.GET.get('category', '')
    
    trainings = Training.objects.all()
    
    if status_filter and status_filter != 'all':
        trainings = trainings.filter(status=status_filter)
    
    if category_filter:
        trainings = trainings.filter(category=category_filter)
    
    try:
        trainings = trainings.prefetch_related('prerequisites')
    except:
        pass
    
    # Build machine type -> training map
    machine_type_map = {}
    try:
        machines_with_training = Machine.objects.exclude(required_training__isnull=True)
        for machine in machines_with_training:
            if machine.machine_name and machine.required_training_id:
                if machine.machine_name not in machine_type_map:
                    machine_type_map[machine.machine_name] = machine.required_training_id
    except:
        pass
    
    data = []
    for t in trainings:
        user_count = 0
        try:
            user_count = t.user_records.filter(status='completed').count()
        except:
            pass
        
        prerequisites = []
        try:
            prerequisites = [
                {'id': p.id, 'name': p.name, 'level': p.level}
                for p in t.prerequisites.all()
            ]
        except:
            pass
        
        data.append({
            'id': t.id,
            'name': t.name,
            'description': getattr(t, 'description', ''),
            'level': getattr(t, 'level', 1),
            'level_display': getattr(t, 'level_display', f'Level {getattr(t, "level", 1)}'),
            'category': getattr(t, 'category', ''),
            'category_id': getattr(t, 'category_id', None),
            'category_name': getattr(t, 'category', ''),
            'machine_type_names': getattr(t, 'machine_type_names', []) or [],
            'prerequisites': prerequisites,
            'duration_minutes': getattr(t, 'duration_minutes', 60),
            'max_participants': getattr(t, 'max_participants', 4),
            'materials_url': getattr(t, 'materials_url', ''),
            'video_url': getattr(t, 'video_url', ''),
            'status': getattr(t, 'status', 'active'),
            'user_count': user_count,
            'created_at': t.created_at.isoformat() if hasattr(t, 'created_at') else None,
            'updated_at': t.updated_at.isoformat() if hasattr(t, 'updated_at') else None,
        })
    
    return JsonResponse({
        'trainings': data,
        'machine_type_training_map': machine_type_map
    })


@login_required
@user_passes_test(is_superuser)
def api_create_training(request):
    """Create a new training"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        name = data.get('name', '').strip()
        if not name:
            return JsonResponse({'success': False, 'error': 'Training name is required'})
        
        category = data.get('category', '').strip()
        if not category:
            return JsonResponse({'success': False, 'error': 'Category is required'})
        
        level = data.get('level', 1)
        if level not in [1, 2, 3]:
            return JsonResponse({'success': False, 'error': 'Level must be 1, 2, or 3'})
        
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
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        training = get_object_or_404(Training, id=training_id)
        
        if 'name' in data:
            training.name = data['name'].strip()
        if 'description' in data:
            training.description = data['description']
        if 'level' in data and data['level'] in [1, 2, 3]:
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
        
        if 'prerequisite_ids' in data:
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
# EXISTING MACHINE TYPES API
# ============================================================================

@login_required
def api_get_existing_machine_types(request):
    """Get unique machine types (machine_name) from existing machines, grouped by category"""
    from django.db.models import Count
    
    # Get unique machine_name values grouped by category with counts
    machine_types = Machine.objects.values('category', 'machine_name').annotate(
        count=Count('id')
    ).order_by('category', 'machine_name')
    
    # Get category info for icons/colors
    categories = MachineCategory.objects.filter(is_active=True)
    category_info = {c.name: {'id': c.id, 'icon': getattr(c, 'icon', '🔧'), 'color': getattr(c, 'color', '#293242')} for c in categories}
    
    # Build machine type -> training map
    training_map = {}
    try:
        machines_with_training = Machine.objects.exclude(required_training__isnull=True)
        for m in machines_with_training:
            if m.machine_name and m.required_training_id:
                training_map[m.machine_name] = m.required_training_id
    except:
        pass
    
    # Group by category
    by_category = {}
    all_types = []
    
    for mt in machine_types:
        cat = mt['category']
        name = mt['machine_name']
        count = mt['count']
        
        if cat not in by_category:
            by_category[cat] = []
        
        cat_info = category_info.get(cat, {})
        type_data = {
            'name': name,
            'category': cat,
            'category_id': cat_info.get('id'),
            'count': count,
            'training_id': training_map.get(name)
        }
        by_category[cat].append(type_data)
        all_types.append(type_data)
    
    return JsonResponse({
        'machine_types': all_types,
        'by_category': by_category,
        'category_info': category_info,
        'machine_type_training_map': training_map,
    })

# ---------------------------------------------------------------------------
# Existing helpers / staff views (keep all your current code above)
# ---------------------------------------------------------------------------

def is_superuser(user):
    return user.is_superuser


@login_required
@user_passes_test(is_superuser)
def staff_machine_directory(request):
    """Staff-specific machine directory with all machines and advanced filtering"""
    machines = Machine.objects.all().order_by('-created_at')

    # Try to prefetch related trainings if the relationship exists
    try:
        machines = machines.prefetch_related('required_trainings')
    except Exception:
        pass

    locations = Location.objects.all().order_by('building', 'name')

    context = {
        'machines': machines,
        'locations': locations,
    }
    return render(request, 'machines/staff_machine_directory.html', context)


@login_required
@user_passes_test(is_superuser)
def machine_detail_api(request, machine_id):
    """API endpoint to get comprehensive machine details for modal"""
    try:
        machine = Machine.objects.get(id=machine_id)

        # Try to get related objects
        try:
            machine = Machine.objects.select_related('location').get(id=machine_id)
        except Exception:
            pass

        # Get training details
        trainings = []

        # Check for required_training (single FK)
        if hasattr(machine, 'required_training') and machine.required_training:
            trainings.append({
                'id': machine.required_training.id,
                'name': machine.required_training.name,
            })

        # Check for required_trainings (M2M)
        if hasattr(machine, 'required_trainings'):
            try:
                if machine.required_trainings.exists():
                    trainings = [
                        {'id': t.id, 'name': t.name}
                        for t in machine.required_trainings.all()
                    ]
            except Exception:
                pass

        # Add level-based training if no custom trainings
        if not trainings:
            if getattr(machine, 'requires_level_1', False):
                trainings.append({'name': 'Level 1 Training', 'type': 'level'})
            if getattr(machine, 'requires_level_2', False):
                trainings.append({'name': 'Level 2 Training', 'type': 'level'})
            if getattr(machine, 'requires_level_3', False):
                trainings.append({'name': 'Level 3 Training', 'type': 'level'})

        # Get location details
        location_str = 'Not assigned'
        location_id = None
        if machine.location:
            if hasattr(machine.location, 'name'):
                location_str = machine.location.name
                location_id = machine.location.id
                if hasattr(machine.location, 'building') and machine.location.building:
                    location_str = f"{machine.location.building} - {machine.location.name}"
            else:
                location_str = str(machine.location)

        data = {
            'id': machine.id,
            'name': machine.name,
            'machine_name': machine.machine_name,
            'category': machine.category,
            'description': machine.description or 'No description available',
            'location': location_str,
            'location_id': location_id,
            'year_bought': str(machine.year_bought) if machine.year_bought else 'N/A',
            'mac_address': machine.mac_address or 'Not connected',
            'image_url': machine.image.url if machine.image else None,
            'map_position_x': float(machine.map_position_x) if machine.map_position_x else None,
            'map_position_y': float(machine.map_position_y) if machine.map_position_y else None,
            'is_reservable': getattr(machine, 'is_reservable', True),
            'trainings': trainings,
            'created_at': machine.created_at.strftime('%B %d, %Y at %I:%M %p'),
            'updated_at': machine.updated_at.strftime('%B %d, %Y at %I:%M %p'),
        }
        return JsonResponse(data)

    except Machine.DoesNotExist:
        return JsonResponse({'error': 'Machine not found'}, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

# ---------------------------------------------------------------------------
# NEW: Student-facing machine detail page with reservation support
# ---------------------------------------------------------------------------

@login_required
def machine_detail(request, machine_id):
    """
    Student-facing machine detail page with reservation and floorplan.
    Provides availability / reservation API URLs for the JS in machine_detail.html.
    """
    machine = get_object_or_404(Machine, id=machine_id)
    location = machine.location

    has_floorplan = False
    floorplan_url = None
    other_machines = Machine.objects.none()

    if location and hasattr(location, "floorplan_image"):
        has_floorplan = bool(location.floorplan_image)
        if has_floorplan:
            floorplan_url = location.floorplan_image.url

        other_machines = (
            location.machines.exclude(id=machine_id)
            .filter(map_position_x__isnull=False, map_position_y__isnull=False)
        )

    context = {
        "machine": machine,
        "location": location,
        "has_floorplan": has_floorplan,
        "floorplan_url": floorplan_url,
        "other_machines": other_machines,
        "today": date.today().isoformat(),
        # URLs consumed by machine_detail.html JS
        "reservationapiurl": f"/reservations/api/machines/{machine.id}/reserve/",
        "availabilityapiurl": f"/reservations/api/machines/{machine.id}/availability/",
    }
    return render(request, "machines/machine_detail.html", context)