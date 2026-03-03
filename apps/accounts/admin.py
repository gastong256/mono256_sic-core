from django.contrib import admin

from hordak.models import Account
from apps.accounts.models import TeacherAccountVisibility


# Hordak registers its own AccountAdmin. We unregister it and replace with ours.
try:
    admin.site.unregister(Account)
except admin.sites.NotRegistered:
    pass


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    """
    Admin interface for hordak Account.

    Only admin users (is_staff=True / role=admin) can modify level-0 and level-1 accounts.
    Level-2 accounts (student subcuentas) are read-only in admin.
    """

    list_display = ("full_code", "name", "type", "level", "is_leaf_node")
    list_filter = ("type",)
    search_fields = ("full_code", "name")
    readonly_fields = ("full_code", "level", "lft", "rght", "tree_id")

    @admin.display(description="leaf?", boolean=True)
    def is_leaf_node(self, obj: Account) -> bool:
        """Return True if the account has no children."""
        return obj.is_leaf_node()

    def has_change_permission(self, request, obj=None) -> bool:
        """Only staff can edit; level-2 accounts are never editable via admin."""
        if not request.user.is_staff:
            return False
        if obj is not None and obj.level >= 2:
            return False
        return True

    def has_delete_permission(self, request, obj=None) -> bool:
        """Only staff can delete; level-2 accounts are never deletable via admin."""
        if not request.user.is_staff:
            return False
        if obj is not None and obj.level >= 2:
            return False
        return True

    def has_add_permission(self, request) -> bool:
        """Only staff can add accounts directly through admin."""
        return request.user.is_staff


@admin.register(TeacherAccountVisibility)
class TeacherAccountVisibilityAdmin(admin.ModelAdmin):
    list_display = ("teacher", "account", "is_visible", "updated_at")
    list_filter = ("is_visible", "teacher")
    search_fields = ("teacher__username", "account__full_code", "account__name")
