from django.db import migrations


def forwards(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(is_staff=True).update(role="admin")


def backwards(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(role="admin", is_superuser=False).update(role="student")


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0002_user_role"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
