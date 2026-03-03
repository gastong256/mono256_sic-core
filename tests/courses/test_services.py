import pytest
from rest_framework.exceptions import ValidationError

from apps.courses.services import create_course, enroll_student
from apps.users.models import User


@pytest.mark.django_db
class TestCourseServices:
    def test_create_course_requires_teacher_role(self):
        student = User.objects.create_user(username="s1", password="x", role=User.Role.STUDENT)

        with pytest.raises(ValidationError):
            create_course(teacher=student, name="Curso 1")

    def test_student_can_only_have_one_course(self):
        teacher = User.objects.create_user(username="t1", password="x", role=User.Role.TEACHER)
        student = User.objects.create_user(username="s1", password="x", role=User.Role.STUDENT)

        course1 = create_course(teacher=teacher, name="Curso 1")
        course2 = create_course(teacher=teacher, name="Curso 2")

        enroll_student(course=course1, student=student)

        with pytest.raises(ValidationError):
            enroll_student(course=course2, student=student)
