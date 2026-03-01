from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class Company(TimeStampedModel):
    """
    Represents a simulated company managed by a student.

    A student acts as a 'accounting firm' and can own one or more companies.
    Teachers can view all companies; students can only access their own.
    """

    name = models.CharField(max_length=255, verbose_name="name")
    tax_id = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="tax ID",
        help_text="Simulated CUIT (optional).",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="companies",
        verbose_name="owner",
        help_text="Student who owns this company.",
    )

    class Meta:
        verbose_name = "company"
        verbose_name_plural = "companies"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name


class CompanyAccount(models.Model):
    """
    Links a hordak Account (level-3 / MPTT level=2) to a Company.

    Only leaf accounts (no children) created by students are linked here.
    Level-1 and level-2 accounts are global and not linked to any company.
    """

    account = models.OneToOneField(
        "hordak.Account",
        on_delete=models.CASCADE,
        related_name="company_account",
        verbose_name="account",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="accounts",
        verbose_name="company",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "company account"
        verbose_name_plural = "company accounts"

    def __str__(self) -> str:
        return f"{self.company.name} — {self.account}"
