from django.contrib import admin
from .models import StudentProfile

# Register your models here.
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "major1", "major2", "minor1", "minor2")
    search_fields = ("user__username", "user__email", "major1", "major2", "minor1", "minor2")