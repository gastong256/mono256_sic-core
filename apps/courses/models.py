from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import TimeStampedModel
from apps.users.models import User


class Course(TimeStampedModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, null=True, blank=True, unique=True)
    teacher = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="courses",
    )

    class Meta:
        ordering = ["name"]

    def clean(self) -> None:
        if self.teacher.role != User.Role.TEACHER:
            raise ValidationError({"teacher": "Course teacher must have teacher role."})

    def __str__(self) -> str:
        return self.code or self.name


class CourseEnrollment(TimeStampedModel):
    student = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="course_enrollment",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )

    class Meta:
        ordering = ["student__username"]

    def clean(self) -> None:
        if self.student.role != User.Role.STUDENT:
            raise ValidationError({"student": "Only student users can be enrolled."})

    def __str__(self) -> str:
        return f"{self.student.username} -> {self.course}"


class CourseDemoCompanyVisibility(TimeStampedModel):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="demo_company_visibilities",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="course_demo_visibilities",
    )
    is_visible = models.BooleanField(default=False)

    class Meta:
        ordering = ["course__name", "company__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "company"],
                name="course_demo_company_unique",
            )
        ]

    def clean(self) -> None:
        if not self.company.is_demo:
            raise ValidationError({"company": "Only demo companies can be configured per course."})

    def __str__(self) -> str:
        return f"{self.course} -> {self.company} ({'visible' if self.is_visible else 'hidden'})"


class CourseSharedCompanyVisibility(TimeStampedModel):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="shared_company_visibilities",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="course_shared_visibilities",
    )
    is_visible = models.BooleanField(default=False)

    class Meta:
        ordering = ["course__name", "company__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "company"],
                name="course_shared_company_unique",
            )
        ]

    def clean(self) -> None:
        if self.company.is_demo:
            raise ValidationError(
                {"company": "Demo companies must be configured through demo visibility."}
            )

    def __str__(self) -> str:
        return f"{self.course} -> {self.company} ({'visible' if self.is_visible else 'hidden'})"
