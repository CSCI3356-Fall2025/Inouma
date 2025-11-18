from django.contrib import admin
from django.utils.html import format_html
from .models import Machine

@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ['image_thumbnail', 'name', 'machine_name', 'category', 'location', 'year_bought', 'training_levels']
    list_filter = ['category', 'location', 'requires_level_1', 'requires_level_2', 'requires_level_3', 'year_bought']
    search_fields = ['name', 'machine_name', 'description', 'mac_address']
    ordering = ['category', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'machine_name', 'category', 'location')
        }),
        ('Image', {
            'fields': ('image', 'image_preview'),
            'description': 'Upload an image for this machine'
        }),
        ('Optional Technical Details', {
            'fields': ('mac_address', 'year_bought', 'description'),
            'classes': ('collapse',),  # This makes it collapsible
        }),
        ('Training Requirements', {
            'fields': ('requires_level_1', 'requires_level_2', 'requires_level_3')
        }),
    )
    
    readonly_fields = ['image_preview']
    
    def image_thumbnail(self, obj):
        """Display small thumbnail in list view"""
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />',
                obj.image.url
            )
        return format_html(
            '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px; opacity: 0.5;" />',
            obj.get_image_url()
        )
    image_thumbnail.short_description = 'Image'
    
    def image_preview(self, obj):
        """Display larger preview in detail view"""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 300px; border-radius: 8px;" />',
                obj.image.url
            )
        return format_html(
            '<img src="{}" style="max-width: 300px; max-height: 300px; border-radius: 8px; opacity: 0.7;" /><br><em>Using default image</em>',
            obj.get_image_url()
        )
    image_preview.short_description = 'Current Image Preview'
    
    def training_levels(self, obj):
        """Display training levels in a concise format"""
        levels = []
        if obj.requires_level_1:
            levels.append('L1')
        if obj.requires_level_2:
            levels.append('L2')
        if obj.requires_level_3:
            levels.append('L3')
        
        if levels:
            return format_html(
                '<span style="background: #ffd700; padding: 2px 8px; border-radius: 4px; font-size: 0.9em;">{}</span>',
                ', '.join(levels)
            )
        return format_html('<span style="color: #999;">None</span>')
    training_levels.short_description = 'Training'