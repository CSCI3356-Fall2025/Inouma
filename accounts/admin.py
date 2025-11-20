from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, StudentProfile, TrainerProfile, Machine, MachineInstance, TrainingReservation, Certification


class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = "Student Profile"
    fk_name = "user"


class TrainerProfileInline(admin.StackedInline):
    model = TrainerProfile
    can_delete = False
    verbose_name_plural = "Trainer Profile"
    fk_name = "user"


class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'school', 'department', 'is_team_lead', 'is_staff', 'is_superuser', 'is_active', 'date_joined')
    list_filter = ('role', 'school', 'is_team_lead', 'is_staff', 'is_superuser', 'is_active')
    ordering = ('-date_joined',)
    search_fields = ('email', 'first_name', 'last_name', 'school', 'department')

    def get_fieldsets(self, request, obj=None):
        """Dynamically show Team Lead fieldset only for Team Member role"""
        fieldsets = (
            (None, {'fields': ('email', 'password', 'role')}),
            (_('Personal info'), {'fields': ('first_name', 'last_name', 'profile_picture', 'school', 'department')}),
            (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
            (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        )
        
        # Only show Team Lead fieldset if user is Team Member or if creating new user
        if obj is None or obj.role == 'Team Member':
            # Insert Team Lead fieldset after Personal info
            fieldsets_list = list(fieldsets)
            fieldsets_list.insert(2, (_('Team Lead'), {
                'fields': ('is_team_lead',), 
                'description': 'Designated to lead other team members (only applies to Team Member role)'
            }))
            return tuple(fieldsets_list)
        
        return fieldsets

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role', 'is_staff', 'is_superuser'),
        }),
    )

    def get_inlines(self, request, obj):
        """Show different profile inlines depending on the user's role."""
        if not obj:
            return []
        if obj.role in ['User', 'Collaborator']:
            return [StudentProfileInline]
        elif obj.role in ['Team Member', 'Staff']:
            return [TrainerProfileInline]
        return []

admin.site.register(User, CustomUserAdmin)
admin.site.register(StudentProfile)
admin.site.register(TrainerProfile)
admin.site.register(Machine)
admin.site.register(MachineInstance)
admin.site.register(TrainingReservation)
admin.site.register(Certification)
