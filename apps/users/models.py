from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.

    Role-based access:
    - admin: platform-level admins (must keep is_staff=True)
    - teacher: course-level supervisors
    - student: operational accounting users
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        TEACHER = "teacher", "Teacher"
        STUDENT = "student", "Student"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        db_index=True,
    )

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        return self.username

    def save(self, *args, **kwargs) -> None:
        if self.is_superuser and self.role != self.Role.ADMIN:
            self.role = self.Role.ADMIN
        if self.role == self.Role.ADMIN:
            self.is_staff = True
        else:
            self.is_staff = False
        super().save(*args, **kwargs)

    @property
    def is_admin_role(self) -> bool:
        return self.role == self.Role.ADMIN

    @property
    def is_teacher_role(self) -> bool:
        return self.role == self.Role.TEACHER

    @property
    def is_student_role(self) -> bool:
        return self.role == self.Role.STUDENT
