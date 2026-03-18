from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0006_company_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="demo_content_sha256",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Canonical content hash used to avoid importing the same demo twice.",
                max_length=64,
                verbose_name="demo content sha256",
            ),
        ),
        migrations.AddField(
            model_name="company",
            name="demo_slug",
            field=models.SlugField(
                blank=True,
                db_index=True,
                default="",
                help_text="Stable slug for imported demo companies.",
                max_length=120,
                verbose_name="demo slug",
            ),
        ),
        migrations.AddField(
            model_name="company",
            name="is_published",
            field=models.BooleanField(
                db_index=True,
                default=True,
                help_text="Controls whether a demo company is globally visible in the application.",
                verbose_name="is published",
            ),
        ),
    ]
