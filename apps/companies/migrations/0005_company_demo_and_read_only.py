from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0004_company_books_closed_until"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="is_demo",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Marks a seeded demo company shared across the system.",
                verbose_name="is demo",
            ),
        ),
        migrations.AddField(
            model_name="company",
            name="is_read_only",
            field=models.BooleanField(
                default=False,
                help_text="If true, accounting writes and metadata updates are blocked.",
                verbose_name="is read only",
            ),
        ),
    ]
