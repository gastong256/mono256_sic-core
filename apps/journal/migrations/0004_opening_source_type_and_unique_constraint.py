from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("journal", "0003_optimize_reporting_indexes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="journalentry",
            name="source_type",
            field=models.CharField(
                choices=[
                    ("OPENING", "Apertura"),
                    ("MANUAL", "Manual"),
                    ("INVOICE", "Factura"),
                    ("RECEIPT", "Recibo"),
                    ("OTHER", "Otro"),
                ],
                default="MANUAL",
                max_length=10,
                verbose_name="tipo de comprobante",
            ),
        ),
        migrations.AddConstraint(
            model_name="journalentry",
            constraint=models.UniqueConstraint(
                condition=models.Q(("source_type", "OPENING")),
                fields=("company",),
                name="one_opening_entry_per_company",
            ),
        ),
    ]
