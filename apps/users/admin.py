from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.users.models import RegistrationCodeConfig, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_staff",
        "date_joined",
    )
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("username", "email")

    fieldsets = BaseUserAdmin.fieldsets + (("Role", {"fields": ("role",)}),)
    add_fieldsets = BaseUserAdmin.add_fieldsets + (("Role", {"fields": ("role",)}),)


@admin.register(RegistrationCodeConfig)
class RegistrationCodeConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "window_minutes", "allow_previous_window", "created_at", "updated_at")
