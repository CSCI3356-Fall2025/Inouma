from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .models import Location
from .forms import LocationForm

@staff_member_required
def location_management(request):
    """View for managing all locations - accessible by all staff"""
    locations = Location.objects.all()
    
    # Group by floor for display
    locations_by_floor = {}
    for location in locations:
        floor = location.floor
        if floor not in locations_by_floor:
            locations_by_floor[floor] = []
        locations_by_floor[floor].append(location)
    
    context = {
        'locations': locations,
        'locations_by_floor': locations_by_floor,
    }
    return render(request, 'locations/locations_list.html', context)

@staff_member_required
def add_location(request):
    """Add a new location"""
    if request.method == 'POST':
        form = LocationForm(request.POST, request.FILES)
        if form.is_valid():
            location = form.save()
            messages.success(request, f'Location "{location.name}" added successfully!')
            return redirect('location_management')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = LocationForm()
    
    context = {'form': form, 'action': 'Add'}
    return render(request, 'locations/location_form.html', context)

@staff_member_required
def edit_location(request, location_id):
    """Edit an existing location"""
    location = get_object_or_404(Location, id=location_id)
    
    if request.method == 'POST':
        form = LocationForm(request.POST, request.FILES, instance=location)
        if form.is_valid():
            location = form.save()
            messages.success(request, f'Location "{location.name}" updated successfully!')
            return redirect('location_management')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = LocationForm(instance=location)
    
    context = {
        'form': form,
        'action': 'Edit',
        'location': location
    }
    return render(request, 'locations/location_form.html', context)

@staff_member_required
def delete_location(request, location_id):
    """Delete a location"""
    location = get_object_or_404(Location, id=location_id)
    location_name = location.name
    location.delete()
    messages.success(request, f'Location "{location_name}" deleted successfully!')
    return redirect('location_management')
