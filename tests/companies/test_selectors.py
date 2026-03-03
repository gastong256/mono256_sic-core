import pytest

from apps.companies.models import Company
from apps.companies.selectors import list_companies
from apps.courses.services import create_course, enroll_student
from apps.users.models import User


@pytest.mark.django_db
class TestCompanySelectorsByRole:
    def test_teacher_sees_only_enrolled_student_companies(self):
        teacher = User.objects.create_user(username="teacher", password="x", role=User.Role.TEACHER)
        student_in = User.objects.create_user(username="s_in", password="x", role=User.Role.STUDENT)
        student_out = User.objects.create_user(username="s_out", password="x", role=User.Role.STUDENT)

        course = create_course(teacher=teacher, name="A")
        enroll_student(course=course, student=student_in)

        c1 = Company.objects.create(name="C1", owner=student_in)
        Company.objects.create(name="C2", owner=student_out)

        visible_ids = set(list_companies(user=teacher).values_list("id", flat=True))

        assert c1.id in visible_ids
        assert len(visible_ids) == 1
