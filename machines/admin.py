from django.contrib import admin
from .models import Machine, TrainingType, Training, UserTrainingRecord, MachineCategory


@admin.register(MachineCategory)
class MachineCategoryAdmin(admin.ModelAdmin):
    """Machine category admin"""
    list_display = ('name', 'icon', 'machine_count', 'display_order', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    ordering = ('display_order', 'name')
    list_editable = ('display_order', 'is_active')


@admin.register(TrainingType)
class TrainingTypeAdmin(admin.ModelAdmin):
    """Legacy training type admin"""
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Training)
class TrainingAdmin(admin.ModelAdmin):
    """Training admin - training courses"""
    list_display = ('name', 'level', 'category', 'duration_minutes', 'max_participants', 'status', 'created_at')
    list_filter = ('level', 'category', 'status')
    search_fields = ('name', 'description', 'category')
    filter_horizontal = ('prerequisites',)
    ordering = ('category', 'level', 'name')
    raw_id_fields = ('created_by',)
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'level', 'category', 'status')
        }),
        ('Machine Types', {
            'fields': ('machine_type_names',),
            'description': 'JSON list of machine_name values this training qualifies users for'
        }),
        ('Prerequisites', {
            'fields': ('prerequisites',),
            'description': 'Other trainings required before this one',
            'classes': ('collapse',)
        }),
        ('Training Details', {
            'fields': ('duration_minutes', 'max_participants', 'materials_url', 'video_url')
        }),
        ('Metadata', {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )


@admin.register(UserTrainingRecord)
class UserTrainingRecordAdmin(admin.ModelAdmin):
    """User training record admin - tracks completed trainings"""
    list_display = ('user', 'training', 'status', 'completed_at', 'trainer', 'is_valid_display')
    list_filter = ('status', 'training__category', 'training__level')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'training__name')
    raw_id_fields = ('user', 'trainer')
    ordering = ('-completed_at',)
    date_hierarchy = 'completed_at'
    
    def is_valid_display(self, obj):
        return obj.is_valid
    is_valid_display.boolean = True
    is_valid_display.short_description = 'Valid'


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    """Machine admin"""
    list_display = ('name', 'machine_name', 'status', 'category', 'location', 'manufacturer', 'created_at')
    list_editable = ('status',)
    list_filter = ('status', 'category', 'location', 'manufacturer', 'requires_level_1', 'requires_level_2', 'requires_level_3')
    search_fields = ('name', 'machine_name', 'category', 'manufacturer', 'model_number')
    filter_horizontal = ('required_trainings',)
    actions = ('mark_as_broken', 'mark_as_maintenance', 'mark_as_active')
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'machine_name', 'category', 'location', 'description', 'image')
        }),
        ('Machine Details', {
            'fields': ('manufacturer', 'model_number', 'documentation_url'),
            'classes': ('collapse',)
        }),
        ('Legacy Training Requirements', {
            'fields': ('required_trainings', 'requires_level_1', 'requires_level_2', 'requires_level_3'),
            'classes': ('collapse',)
        }),
        ('Technical Details', {
            'fields': ('mac_address', 'year_bought'),
            'classes': ('collapse',)
        }),
        ('Floorplan Position', {
            'fields': ('map_position_x', 'map_position_y'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

    def mark_as_broken(self, request, queryset):
        updated = queryset.update(status='broken')
        self.message_user(request, f"Marked {updated} machine(s) as broken.")
    mark_as_broken.short_description = 'Mark selected machines as Broken'

    def mark_as_maintenance(self, request, queryset):
        updated = queryset.update(status='maintenance')
        self.message_user(request, f"Marked {updated} machine(s) as under Maintenance.")
    mark_as_maintenance.short_description = 'Mark selected machines as Maintenance'

    def mark_as_active(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f"Marked {updated} machine(s) as Active.")
    mark_as_active.short_description = 'Mark selected machines as Active'
    