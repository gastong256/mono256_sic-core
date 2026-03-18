from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class Company(TimeStampedModel):
    name = models.CharField(max_length=255, verbose_name="name")
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="description",
        help_text="Optional business description for a more realistic simulation.",
    )
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
    books_closed_until = models.DateField(
        null=True,
        blank=True,
        verbose_name="books closed until",
        help_text="Entries on or before this date are locked.",
    )
    is_demo = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="is demo",
        help_text="Marks a seeded demo company shared across the system.",
    )
    is_read_only = models.BooleanField(
        default=False,
        verbose_name="is read only",
        help_text="If true, accounting writes and metadata updates are blocked.",
    )
    is_published = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="is published",
        help_text="Controls whether a demo company is globally visible in the application.",
    )
    demo_slug = models.SlugField(
        max_length=120,
        blank=True,
        default="",
        db_index=True,
        verbose_name="demo slug",
        help_text="Stable slug for imported demo companies.",
    )
    demo_content_sha256 = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        verbose_name="demo content sha256",
        help_text="Canonical content hash used to avoid importing the same demo twice.",
    )

    class Meta:
        verbose_name = "company"
        verbose_name_plural = "companies"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name


class CompanyAccount(models.Model):
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
