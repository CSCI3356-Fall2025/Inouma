from django.contrib import admin
from .models import (
    Semester, DailyOperatingHours, LocationGroup, ShiftRequirement,
    TeamGroup, TeamMemberProfile, Unavailability, Shift, SchedulePublication,
    ShiftChangeRequest
)


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ('name', 'semester_type', 'year', 'start_date', 'end_date', 'is_active')
    list_filter = ('semester_type', 'year', 'is_active')
    search_fields = ('name',)
    ordering = ('-start_date',)


class DailyOperatingHoursInline(admin.TabularInline):
    model = DailyOperatingHours
    extra = 0
    fields = ('day_of_week', 'space_open_time', 'space_close_time', 
              'open_hours_start', 'open_hours_end', 'is_closed')


@admin.register(DailyOperatingHours)
class DailyOperatingHoursAdmin(admin.ModelAdmin):
    list_display = ('semester', 'day_of_week', 'is_closed',
                    'open_hours_start', 'open_hours_end', 
                    'training_start', 'training_end')
    list_filter = ('semester', 'day_of_week', 'is_closed')
    ordering = ('semester', 'day_of_week')


@admin.register(LocationGroup)
class LocationGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_location_count', 'created_at')
    search_fields = ('name', 'description')
    filter_horizontal = ('locations',)
    
    def get_location_count(self, obj):
        return obj.locations.count()
    get_location_count.short_description = 'Locations'


@admin.register(TeamGroup)
class TeamGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'lead', 'color', 'get_member_count')
    search_fields = ('name', 'description')
    list_filter = ('lead',)
    
    def get_member_count(self, obj):
        return obj.members.count()
    get_member_count.short_description = 'Members'


@admin.register(ShiftRequirement)
class ShiftRequirementAdmin(admin.ModelAdmin):
    list_display = ('semester', 'day_of_week', 'time_start', 'time_end', 
                    'get_target', 'hosts_required', 'floaters_required', 'is_peak_hours')
    list_filter = ('semester', 'day_of_week', 'is_peak_hours')
    ordering = ('semester', 'day_of_week', 'time_start')
    
    def get_target(self, obj):
        if obj.location:
            return obj.location.name
        elif obj.location_group:
            return obj.location_group.name
        return "General"
    get_target.short_description = 'Location/Group'


@admin.register(TeamMemberProfile)
class TeamMemberProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'team_group', 'role', 'is_trainer', 'is_team_lead', 
                    'graduation_year', 'birthday', 'max_weekly_hours')
    list_filter = ('role', 'team_group', 'is_trainer', 'is_team_lead', 'graduation_year')
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'phone')
    ordering = ('user__last_name', 'user__first_name')
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Personal Info', {
            'fields': ('phone', 'birthday', 'graduation_year', 'profile_image_url')
        }),
        ('Team Assignment', {
            'fields': ('team_group', 'team', 'role', 'is_trainer', 'is_team_lead', 'is_active')
        }),
        ('Scheduling', {
            'fields': ('semester', 'min_weekly_hours', 'max_weekly_hours', 'shift_preference')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Unavailability)
class UnavailabilityAdmin(admin.ModelAdmin):
    list_display = ('user', 'semester', 'day_of_week', 'start_time', 'end_time', 'reason')
    list_filter = ('semester', 'day_of_week')
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'reason')
    ordering = ('semester', 'user', 'day_of_week', 'start_time')


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'start_time', 'end_time', 'shift_type', 
                    'get_location_info', 'status', 'duration_hours')
    list_filter = ('semester', 'shift_type', 'status', 'date')
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 
                     'team_category', 'notes')
    ordering = ('date', 'start_time')
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('semester', 'user', 'date', 'start_time', 'end_time', 'shift_type')
        }),
        ('Location/Team', {
            'fields': ('location', 'location_group', 'team_category')
        }),
        ('Status', {
            'fields': ('status', 'original_user', 'swap_requested_with', 
                       'cancellation_reason', 'cancelled_at')
        }),
        ('Approval', {
            'fields': ('approved_by', 'approved_at')
        }),
        ('Additional', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def get_location_info(self, obj):
        if obj.shift_type == 'open_hours':
            if obj.location:
                return obj.location.name
            elif obj.location_group:
                return obj.location_group.name
        elif obj.shift_type == 'training':
            return f"{obj.team_category} Training"
        elif obj.shift_type == 'floater':
            return "Floater"
        return "-"
    get_location_info.short_description = 'Assignment'


@admin.register(SchedulePublication)
class SchedulePublicationAdmin(admin.ModelAdmin):
    list_display = ('semester', 'published_by', 'published_at', 
                    'weeks_count', 'recipients_count', 'calendar_invites_sent', 
                    'email_sent', 'status')
    list_filter = ('semester', 'calendar_invites_sent', 'email_sent', 'status')
    ordering = ('-published_at',)
    readonly_fields = ('published_at',)


@admin.register(ShiftChangeRequest)
class ShiftChangeRequestAdmin(admin.ModelAdmin):
    list_display = ('requested_by', 'request_type', 'shift', 'status', 
                    'created_at', 'reviewed_by')
    list_filter = ('request_type', 'status', 'created_at')
    search_fields = ('requested_by__first_name', 'requested_by__last_name', 
                     'requested_by__email', 'cancellation_reason', 'admin_notes')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'reviewed_at')
    
    fieldsets = (
        ('Request Information', {
            'fields': ('shift', 'requested_by', 'request_type', 'created_at')
        }),
        ('Swap Details', {
            'fields': ('swap_with_user', 'swap_with_shift', 'swap_accepted_by_other_user'),
            'classes': ('collapse',)
        }),
        ('Amendment Details', {
            'fields': ('proposed_date', 'proposed_start_time', 'proposed_end_time'),
            'classes': ('collapse',)
        }),
        ('Cancellation Details', {
            'fields': ('cancellation_reason',),
            'classes': ('collapse',)
        }),
        ('Review', {
            'fields': ('status', 'reviewed_by', 'reviewed_at', 'admin_notes')
        }),
    )