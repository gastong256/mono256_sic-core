from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0005_company_demo_and_read_only"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="description",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Optional business description for a more realistic simulation.",
                verbose_name="description",
            ),
        ),
    ]
