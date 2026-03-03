from decimal import Decimal

from django.contrib import admin

from apps.journal.models import JournalEntry, JournalEntryLine


class JournalEntryLineInline(admin.TabularInline):
    model = JournalEntryLine
    extra = 0
    readonly_fields = ("account", "type", "amount")
    can_delete = False

    def has_add_permission(self, request, obj=None) -> bool:
        return False


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = (
        "entry_number",
        "company",
        "date",
        "description",
        "source_type",
        "source_ref",
        "created_by",
        "total_debit",
    )
    list_filter = ("company", "source_type", "date")
    search_fields = ("description", "source_ref", "company__name")
    readonly_fields = (
        "transaction",
        "company",
        "entry_number",
        "date",
        "description",
        "source_type",
        "source_ref",
        "created_by",
        "created_at",
        "updated_at",
    )
    inlines = [JournalEntryLineInline]

    @admin.display(description="Total Débito")
    def total_debit(self, obj: JournalEntry) -> Decimal:
        return sum(
            (line.amount for line in obj.lines.filter(type=JournalEntryLine.LineType.DEBIT)),
            Decimal("0"),
        )

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
