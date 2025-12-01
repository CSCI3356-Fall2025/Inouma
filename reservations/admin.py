"""
Reservations App Admin Configuration
"""

from django.contrib import admin
from .models import (
    MachineReservation,
    ReservationWaitlist,
    TrainingSession,
    TrainingBooking,
    MachineMaintenance,
    BlackoutPeriod,
)


@admin.register(MachineReservation)
class MachineReservationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'machine', 'date', 'start_time', 'end_time', 
        'status', 'created_at'
    ]
    list_filter = ['status', 'date', 'machine__category']
    search_fields = ['user__email', 'user__first_name', 'machine__name']
    date_hierarchy = 'date'
    ordering = ['-date', '-start_time']
    
    raw_id_fields = ['user', 'machine']


@admin.register(ReservationWaitlist)
class ReservationWaitlistAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'machine', 'date', 'preferred_start_time',
        'status', 'created_at'
    ]
    list_filter = ['status', 'date']
    search_fields = ['user__email', 'machine__name']
    ordering = ['-created_at']
    
    raw_id_fields = ['user', 'machine']


@admin.register(TrainingSession)
class TrainingSessionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'training', 'trainer', 'date', 'start_time', 'end_time',
        'max_participants', 'current_participants', 'status'
    ]
    list_filter = ['status', 'date', 'training__category']
    search_fields = ['training__name', 'trainer__email']
    date_hierarchy = 'date'
    ordering = ['-date', '-start_time']
    
    raw_id_fields = ['trainer', 'training', 'location', 'source_shift']
    
    def current_participants(self, obj):
        return obj.current_participants
    current_participants.short_description = 'Participants'


@admin.register(TrainingBooking)
class TrainingBookingAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'session', 'status', 'registered_at', 'completed_at'
    ]
    list_filter = ['status', 'session__date']
    search_fields = ['user__email', 'session__training__name']
    ordering = ['-registered_at']
    
    raw_id_fields = ['user', 'session', 'completed_by']


@admin.register(MachineMaintenance)
class MachineMaintenanceAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'machine', 'issue_short', 'priority', 'status', 
        'machine_offline', 'reported_at'
    ]
    list_filter = ['status', 'priority', 'machine_offline', 'machine__category']
    search_fields = ['machine__name', 'issue_description']
    ordering = ['-reported_at']
    
    raw_id_fields = ['machine', 'reported_by', 'acknowledged_by', 'resolved_by']
    
    def issue_short(self, obj):
        return obj.issue_description[:50] + '...' if len(obj.issue_description) > 50 else obj.issue_description
    issue_short.short_description = 'Issue'


@admin.register(BlackoutPeriod)
class BlackoutPeriodAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'scope', 'get_target', 'start_datetime', 'end_datetime',
        'blocks_reservations', 'blocks_trainings', 'reason_short'
    ]
    list_filter = ['scope', 'blocks_reservations', 'blocks_trainings']
    search_fields = ['reason', 'category', 'machine__name', 'location__name']
    ordering = ['-start_datetime']
    
    raw_id_fields = ['location', 'machine', 'created_by']
    
    def get_target(self, obj):
        if obj.scope == 'global':
            return 'All Machines'
        elif obj.scope == 'location' and obj.location:
            return f'Location: {obj.location.name}'
        elif obj.scope == 'category' and obj.category:
            return f'Category: {obj.category}'
        elif obj.scope == 'machine' and obj.machine:
            return f'Machine: {obj.machine.name}'
        return '-'
    get_target.short_description = 'Target'
    
    def reason_short(self, obj):
        return obj.reason[:30] + '...' if len(obj.reason) > 30 else obj.reason
    reason_short.short_description = 'Reason'