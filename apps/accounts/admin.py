from django.contrib import admin

from apps.accounts.models import TeacherAccountVisibility
from hordak.models import Account

try:
    admin.site.unregister(Account)
except admin.sites.NotRegistered:
    pass


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("full_code", "name", "type", "level", "is_leaf_node")
    list_filter = ("type",)
    search_fields = ("full_code", "name")
    readonly_fields = ("full_code", "level", "lft", "rght", "tree_id")

    @admin.display(description="leaf?", boolean=True)
    def is_leaf_node(self, obj: Account) -> bool:
        return obj.is_leaf_node()

    def has_change_permission(self, request, obj=None) -> bool:
        if not request.user.is_staff:
            return False
        if obj is not None and obj.level >= 2:
            return False
        return True

    def has_delete_permission(self, request, obj=None) -> bool:
        if not request.user.is_staff:
            return False
        if obj is not None and obj.level >= 2:
            return False
        return True

    def has_add_permission(self, request) -> bool:
        return request.user.is_staff


@admin.register(TeacherAccountVisibility)
class TeacherAccountVisibilityAdmin(admin.ModelAdmin):
    list_display = ("teacher", "account", "is_visible", "updated_at")
    list_filter = ("is_visible", "teacher")
    search_fields = ("teacher__username", "account__full_code", "account__name")
