from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django import forms
from .models import User, StudentProfile, TrainerProfile, Certification


def get_category_choices():
    """Get category choices from MachineCategory model"""
    choices = [('', '-- Select Team --')]
    try:
        from machines.models import MachineCategory
        categories = MachineCategory.objects.filter(is_active=True).order_by('display_order', 'name')
        for cat in categories:
            display = f"{cat.icon} {cat.name}" if cat.icon else cat.name
            choices.append((cat.name, display))
    except:
        # Fallback if MachineCategory doesn't exist yet
        try:
            from machines.models import Machine
            if hasattr(Machine, 'CATEGORY_CHOICES'):
                choices.extend(list(Machine.CATEGORY_CHOICES))
        except:
            # Final fallback
            choices.extend([
                ('Laser', 'Laser'),
                ('Vinyl', 'Vinyl'),
                ('Woodworking', 'Woodworking'),
                ('Textile', 'Textile'),
                ('Metalworking', 'Metalworking'),
                ('3D Printing', '3D Printing'),
                ('Electronics', 'Electronics'),
            ])
    return choices


class UserAdminForm(forms.ModelForm):
    """Custom form for User admin with dynamic team assignment choices"""
    
    class Meta:
        model = User
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if 'team_assignment' in self.fields:
            # Get fresh category choices each time form is loaded
            self.fields['team_assignment'].widget = forms.Select(choices=get_category_choices())
    
    def clean(self):
        cleaned_data = super().clean()
        is_team_lead = cleaned_data.get('is_team_lead', False)
        is_trainer = cleaned_data.get('is_trainer', False)
        team_assignment = cleaned_data.get('team_assignment', '')
        
        # Team leads must have team assignment
        if is_team_lead and not team_assignment:
            self.add_error('team_assignment', 'Team assignment is required for team leads.')
        
        # Auto-set trainer if team lead
        if is_team_lead and not is_trainer:
            cleaned_data['is_trainer'] = True
        
        return cleaned_data


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserAdminForm
    
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_team_lead', 'is_trainer', 'team_assignment', 'is_staff', 'is_active')
    list_filter = ('role', 'is_team_lead', 'is_trainer', 'team_assignment', 'is_staff', 'is_active', 'school')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal Info'), {'fields': ('first_name', 'last_name', 'profile_picture')}),
        (_('Role & Permissions'), {'fields': ('role', 'is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Team Member Settings'), {
            'fields': ('is_team_lead', 'is_trainer', 'team_assignment'),
            'classes': ('collapse',),
            'description': 'These fields only apply when Role is "Team Member". Team Leads are automatically Trainers.'
        }),
        (_('School Info'), {'fields': ('school', 'department')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'role'),
        }),
        (_('Team Member Settings'), {
            'classes': ('wide',),
            'fields': ('is_team_lead', 'is_trainer', 'team_assignment'),
            'description': 'These fields only apply when Role is "Team Member". Team Leads are automatically Trainers.'
        }),
    )
    
    def save_model(self, request, obj, form, change):
        # Ensure team lead is also trainer
        if obj.is_team_lead:
            obj.is_trainer = True
        super().save_model(request, obj, form, change)

    class Media:
        js = ('js/team_member_toggle.js',)


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'major1', 'graduation_year', 'birthday')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'major1')
    list_filter = ('graduation_year',)


@admin.register(TrainerProfile)
class TrainerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialty')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'specialty')


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'issued_at', 'expires_at')
    search_fields = ('user__email', 'name')
    list_filter = ('name', 'issued_at')
    