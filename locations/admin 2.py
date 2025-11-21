from django.contrib import admin
from .models import Location

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'building', 'floor', 'num_stations', 'capacity', 'created_at']
    list_filter = ['floor', 'building']
    search_fields = ['name', 'building', 'floor']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'building', 'floor')
        }),
        ('Capacity', {
            'fields': ('num_stations', 'capacity')
        }),
        ('Machine Types', {
            'fields': ('machine_types',)
        }),
        ('Floorplan', {
            'fields': ('floorplan_image',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )