from django.contrib import admin

from apps.companies.models import Company, CompanyAccount


class CompanyAccountInline(admin.TabularInline):
    """Inline display of level-3 accounts linked to this company."""

    model = CompanyAccount
    extra = 0
    readonly_fields = ("account", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None) -> bool:
        return False


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """Admin interface for Company."""

    list_display = ("name", "owner", "account_count", "created_at")
    list_filter = ("owner",)
    search_fields = ("name", "owner__username")
    readonly_fields = ("created_at", "updated_at")
    inlines = [CompanyAccountInline]

    @admin.display(description="# accounts")
    def account_count(self, obj: Company) -> int:
        """Return the number of level-3 accounts linked to this company."""
        return obj.accounts.count()
