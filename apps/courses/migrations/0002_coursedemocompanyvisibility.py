from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0005_company_demo_and_read_only"),
        ("courses", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CourseDemoCompanyVisibility",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_visible", models.BooleanField(default=False)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="course_demo_visibilities",
                        to="companies.company",
                    ),
                ),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="demo_company_visibilities",
                        to="courses.course",
                    ),
                ),
            ],
            options={
                "ordering": ["course__name", "company__name"],
            },
        ),
        migrations.AddConstraint(
            model_name="coursedemocompanyvisibility",
            constraint=models.UniqueConstraint(
                fields=("course", "company"),
                name="course_demo_company_unique",
            ),
        ),
    ]
