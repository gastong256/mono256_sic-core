from django.db import models

from apps.common.models import TimeStampedModel
from apps.companies.models import Company
from apps.journal.models import JournalEntry


class ClosingSnapshot(TimeStampedModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="closing_snapshots",
        verbose_name="company",
    )
    patrimonial_closing_entry = models.OneToOneField(
        JournalEntry,
        on_delete=models.PROTECT,
        related_name="closing_snapshot",
        verbose_name="patrimonial closing entry",
    )
    reopening_entry = models.OneToOneField(
        JournalEntry,
        on_delete=models.PROTECT,
        related_name="reopening_snapshot",
        verbose_name="reopening entry",
    )
    closing_date = models.DateField(verbose_name="closing date")
    reopening_date = models.DateField(verbose_name="reopening date")
    balance_sheet_payload = models.JSONField(default=dict, verbose_name="balance sheet payload")
    income_statement_payload = models.JSONField(
        default=dict,
        verbose_name="income statement payload",
    )

    class Meta:
        ordering = ["-closing_date", "-id"]
        indexes = [
            models.Index(
                fields=["company", "closing_date"],
                name="closing_snapshot_cmp_dt_idx",
            ),
        ]
        verbose_name = "closing snapshot"
        verbose_name_plural = "closing snapshots"

    def __str__(self) -> str:
        return f"{self.company} — closing snapshot {self.closing_date}"


class ClosingSnapshotLine(models.Model):
    snapshot = models.ForeignKey(
        ClosingSnapshot,
        on_delete=models.CASCADE,
        related_name="lines",
        verbose_name="snapshot",
    )
    account = models.ForeignKey(
        "hordak.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="account",
    )
    account_code = models.CharField(max_length=32, verbose_name="account code")
    account_name = models.CharField(max_length=255, verbose_name="account name")
    account_type = models.CharField(max_length=8, verbose_name="account type")
    root_code = models.CharField(max_length=8, verbose_name="root code")
    parent_code = models.CharField(max_length=16, verbose_name="parent code")
    debit_balance = models.DecimalField(max_digits=15, decimal_places=2, default="0.00")
    credit_balance = models.DecimalField(max_digits=15, decimal_places=2, default="0.00")

    class Meta:
        ordering = ["account_code", "id"]
        indexes = [
            models.Index(
                fields=["snapshot", "root_code", "account_code"],
                name="closing_snap_line_idx",
            ),
        ]
        verbose_name = "closing snapshot line"
        verbose_name_plural = "closing snapshot lines"

    def __str__(self) -> str:
        return f"{self.snapshot} — {self.account_code} {self.account_name}"
