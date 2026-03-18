from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("companies", "0006_company_description"),
        ("journal", "0005_expand_source_type_for_closing_entries"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClosingSnapshot",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("closing_date", models.DateField(verbose_name="closing date")),
                ("reopening_date", models.DateField(verbose_name="reopening date")),
                (
                    "balance_sheet_payload",
                    models.JSONField(default=dict, verbose_name="balance sheet payload"),
                ),
                (
                    "income_statement_payload",
                    models.JSONField(default=dict, verbose_name="income statement payload"),
                ),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="closing_snapshots",
                        to="companies.company",
                        verbose_name="company",
                    ),
                ),
                (
                    "patrimonial_closing_entry",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="closing_snapshot",
                        to="journal.journalentry",
                        verbose_name="patrimonial closing entry",
                    ),
                ),
                (
                    "reopening_entry",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reopening_snapshot",
                        to="journal.journalentry",
                        verbose_name="reopening entry",
                    ),
                ),
            ],
            options={
                "verbose_name": "closing snapshot",
                "verbose_name_plural": "closing snapshots",
                "ordering": ["-closing_date", "-id"],
            },
        ),
        migrations.CreateModel(
            name="ClosingSnapshotLine",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("account_code", models.CharField(max_length=32, verbose_name="account code")),
                ("account_name", models.CharField(max_length=255, verbose_name="account name")),
                ("account_type", models.CharField(max_length=8, verbose_name="account type")),
                ("root_code", models.CharField(max_length=8, verbose_name="root code")),
                ("parent_code", models.CharField(max_length=16, verbose_name="parent code")),
                (
                    "debit_balance",
                    models.DecimalField(decimal_places=2, default="0.00", max_digits=15),
                ),
                (
                    "credit_balance",
                    models.DecimalField(decimal_places=2, default="0.00", max_digits=15),
                ),
                (
                    "account",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="hordak.account",
                        verbose_name="account",
                    ),
                ),
                (
                    "snapshot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lines",
                        to="closing.closingsnapshot",
                        verbose_name="snapshot",
                    ),
                ),
            ],
            options={
                "verbose_name": "closing snapshot line",
                "verbose_name_plural": "closing snapshot lines",
                "ordering": ["account_code", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="closingsnapshot",
            index=models.Index(
                fields=["company", "closing_date"], name="closing_snapshot_cmp_dt_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="closingsnapshotline",
            index=models.Index(
                fields=["snapshot", "root_code", "account_code"],
                name="closing_snap_line_idx",
            ),
        ),
    ]
