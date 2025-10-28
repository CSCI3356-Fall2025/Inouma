from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, StudentProfile


# --- Custom User Admin ---
class CustomUserAdmin(UserAdmin):
    # Display these fields in the admin user list
    list_display = ('email', 'is_staff', 'is_superuser', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    ordering = ('-date_joined',)
    search_fields = ('email',)

    # Field layout when editing a user
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('Firebase Info'), {'fields': ('firebase_uid',)}),
    )

    # Field layout when creating a new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_superuser'),
        }),
    )


# --- Student Profile Admin ---
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "major1", "major2", "minor1", "minor2")
    search_fields = ("user__email", "major1", "major2", "minor1", "minor2")


# --- Register models ---
admin.site.register(User, CustomUserAdmin)
admin.site.register(StudentProfile, StudentProfileAdmin)
