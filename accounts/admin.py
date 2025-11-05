from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, StudentProfile, TrainerProfile


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
    list_display = ('email', 'role', 'is_staff', 'is_superuser', 'is_active', 'date_joined')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    ordering = ('-date_joined',)
    search_fields = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'password', 'role')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('Firebase Info'), {'fields': ('firebase_uid',)}),
    )

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
        if obj.role == 'student':
            return [StudentProfileInline]
        elif obj.role == 'trainer':
            return [TrainerProfileInline]
        return []

admin.site.register(User, CustomUserAdmin)
admin.site.register(StudentProfile)
admin.site.register(TrainerProfile)
