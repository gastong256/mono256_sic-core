from django.contrib import admin

from apps.companies.models import Company, CompanyAccount


class CompanyAccountInline(admin.TabularInline):
    model = CompanyAccount
    extra = 0
    readonly_fields = ("account", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None) -> bool:
        return False


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "books_closed_until", "account_count", "created_at")
    list_filter = ("owner",)
    search_fields = ("name", "owner__username")
    readonly_fields = ("created_at", "updated_at")
    inlines = [CompanyAccountInline]

    @admin.display(description="# accounts")
    def account_count(self, obj: Company) -> int:
        return obj.accounts.count()
