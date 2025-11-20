from django.contrib import admin
from django.utils.html import format_html
from .models import Machine, TrainingType


@admin.register(TrainingType)
class TrainingTypeAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name', 'description']


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = [
        'image_thumbnail',
        'name',
        'machine_name',
        'category',
        'location',
        'year_bought',
        'training_levels',   # now prefers explicit trainings but keeps L1/L2/L3 fallback
    ]
    list_filter = [
        'category',
        'location',
        'requires_level_1',
        'requires_level_2',
        'requires_level_3',
        'year_bought',
        'required_trainings',
    ]
    search_fields = ['name', 'machine_name', 'description', 'mac_address']
    ordering = ['category', 'name']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'machine_name', 'category', 'location')
        }),
        ('Image', {
            'fields': ('image',),
            'description': 'Upload an image or leave blank to use the default machine image.'
        }),
        ('Description & Details', {
            'fields': ('description', 'mac_address', 'year_bought')
        }),
        ('Training Requirements', {
            'fields': (
                'requires_level_1',
                'requires_level_2',
                'requires_level_3',
                'required_trainings',
            ),
            'description': (
                'Level 1/2/3 flags are kept for backwards compatibility. '
                'Use "Required trainings" to assign specific credentials, '
                'for example "Laser Cutter Training".'
            ),
        }),
    )

    def image_thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 60px; height: auto; border-radius: 4px;" />',
                obj.image.url
            )
        return format_html(
            '<div style="width: 60px; height: 40px; background: #f0f0f0; '
            'display: flex; align-items: center; justify-content: center; '
            'color: #999; font-size: 0.7rem; border-radius: 4px;">No image</div>'
        )
    image_thumbnail.short_description = 'Image'

    def training_levels(self, obj):
        """
        What shows up in the “Training” column in the admin list.

        If explicit required_trainings exist, show their names.
        Otherwise fall back to the legacy Level 1/2/3 badges.
        """
        explicit = list(obj.required_trainings.all())
        if explicit:
            names = ', '.join(t.name for t in explicit)
            return format_html(
                '<span style="background:#ffd700;padding:2px 8px;'
                'border-radius:4px;font-size:0.9em;">{}</span>',
                names
            )

        levels = []
        if obj.requires_level_1:
            levels.append('L1')
        if obj.requires_level_2:
            levels.append('L2')
        if obj.requires_level_3:
            levels.append('L3')

        if levels:
            return format_html(
                '<span style="background:#eee;padding:2px 8px;'
                'border-radius:4px;font-size:0.9em;">{}</span>',
                ', '.join(levels)
            )
        return format_html('<span style="color:#999;">None</span>')

    training_levels.short_description = 'Training'
