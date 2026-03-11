from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import TimeStampedModel
from apps.companies.models import Company


class JournalEntry(TimeStampedModel):
    """Immutable accounting entry; once posted it cannot be edited or deleted."""
    class SourceType(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        INVOICE = "INVOICE", "Factura"
        RECEIPT = "RECEIPT", "Recibo"
        OTHER = "OTHER", "Otro"

    transaction = models.OneToOneField(
        "hordak.Transaction",
        on_delete=models.PROTECT,
        null=True,
        related_name="journal_entry",
        verbose_name="transacción",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="journal_entries",
        verbose_name="empresa",
    )
    entry_number = models.PositiveIntegerField(
        verbose_name="número de asiento",
        help_text="Correlativo por empresa, asignado automáticamente.",
    )
    date = models.DateField(verbose_name="fecha")
    description = models.CharField(max_length=500, verbose_name="descripción")
    source_type = models.CharField(
        max_length=10,
        choices=SourceType.choices,
        default=SourceType.MANUAL,
        verbose_name="tipo de comprobante",
    )
    source_ref = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="referencia",
        help_text='Ej.: "Factura A-0001", "Recibo 00123".',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="journal_entries",
        verbose_name="registrado por",
    )
    reversal_of = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reversed_by",
        verbose_name="reversión de",
    )

    class Meta:
        ordering = ["company", "entry_number"]
        unique_together = [("company", "entry_number")]
        indexes = [
            models.Index(
                fields=["company", "date", "entry_number"],
                name="journal_entry_cmp_dt_no_idx",
            ),
            models.Index(
                fields=["date", "entry_number"],
                name="journal_entry_dt_no_idx",
            ),
        ]
        verbose_name = "Asiento contable"
        verbose_name_plural = "Asientos contables"

    def __str__(self) -> str:
        return f"{self.company} — Asiento #{self.entry_number}"

    def save(self, *args, **kwargs) -> None:
        if self.pk is not None:
            raise ValidationError("Los asientos contables son inmutables.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs) -> None:
        raise ValidationError("Los asientos contables no pueden eliminarse.")


class JournalEntryLine(models.Model):
    """Single debit/credit movement line with positive amount."""
    class LineType(models.TextChoices):
        DEBIT = "DEBIT", "Deudora"
        CREDIT = "CREDIT", "Acreedora"

    journal_entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.PROTECT,
        related_name="lines",
        verbose_name="asiento",
    )
    account = models.ForeignKey(
        "hordak.Account",
        on_delete=models.PROTECT,
        verbose_name="cuenta",
    )
    type = models.CharField(
        max_length=6,
        choices=LineType.choices,
        verbose_name="tipo",
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="importe",
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["journal_entry", "account", "type"],
                name="journal_line_je_ac_tp_idx",
            ),
            models.Index(
                fields=["account", "journal_entry"],
                name="journal_line_ac_je_idx",
            ),
        ]
        verbose_name = "Línea de asiento"
        verbose_name_plural = "Líneas de asiento"

    def __str__(self) -> str:
        return f"{self.get_type_display()} {self.amount} — {self.account}"
