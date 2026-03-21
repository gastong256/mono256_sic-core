from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0007_company_demo_publication_metadata"),
        ("courses", "0002_coursedemocompanyvisibility"),
    ]

    operations = [
        migrations.CreateModel(
            name="CourseSharedCompanyVisibility",
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
                        related_name="course_shared_visibilities",
                        to="companies.company",
                    ),
                ),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="shared_company_visibilities",
                        to="courses.course",
                    ),
                ),
            ],
            options={
                "ordering": ["course__name", "company__name"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("course", "company"),
                        name="course_shared_company_unique",
                    )
                ],
            },
        ),
    ]
