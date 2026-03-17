from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("journal", "0004_opening_source_type_and_unique_constraint"),
    ]

    operations = [
        migrations.AlterField(
            model_name="journalentry",
            name="source_type",
            field=models.CharField(
                choices=[
                    ("OPENING", "Apertura"),
                    ("ADJUSTMENT", "Ajuste"),
                    ("RESULT_CLOSING", "Cierre de Resultado"),
                    ("PATRIMONIAL_CLOSING", "Cierre Patrimonial"),
                    ("REOPENING", "Reapertura"),
                    ("MANUAL", "Manual"),
                    ("INVOICE", "Factura"),
                    ("RECEIPT", "Recibo"),
                    ("OTHER", "Otro"),
                ],
                default="MANUAL",
                max_length=24,
                verbose_name="tipo de comprobante",
            ),
        ),
    ]
