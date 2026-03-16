import pytest

from apps.companies.models import Company
from apps.courses.models import CourseDemoCompanyVisibility
from apps.companies.selectors import list_companies
from apps.courses.services import create_course, enroll_student
from apps.users.models import User


@pytest.mark.django_db
class TestCompanySelectorsByRole:
    def test_teacher_sees_only_enrolled_student_companies(self):
        teacher = User.objects.create_user(username="teacher", password="x", role=User.Role.TEACHER)
        student_in = User.objects.create_user(username="s_in", password="x", role=User.Role.STUDENT)
        student_out = User.objects.create_user(
            username="s_out", password="x", role=User.Role.STUDENT
        )

        course = create_course(teacher=teacher, name="A")
        enroll_student(course=course, student=student_in)

        c1 = Company.objects.create(name="C1", owner=student_in)
        Company.objects.create(name="C2", owner=student_out)

        visible_ids = set(list_companies(user=teacher).values_list("id", flat=True))

        assert c1.id in visible_ids
        assert len(visible_ids) == 1

    def test_student_sees_only_demo_companies_enabled_for_their_course(self):
        demo_owner = User.objects.create_user(
            username="demo-owner-selector",
            password="x",
            role=User.Role.ADMIN,
        )
        teacher = User.objects.create_user(
            username="teacher-selector-demo",
            password="x",
            role=User.Role.TEACHER,
        )
        student = User.objects.create_user(
            username="student-selector-demo",
            password="x",
            role=User.Role.STUDENT,
        )

        course = create_course(teacher=teacher, name="Curso Demo Selector")
        enroll_student(course=course, student=student)

        own_company = Company.objects.create(name="Empresa Propia", owner=student)
        visible_demo = Company.objects.create(
            name="Demo Visible",
            owner=demo_owner,
            is_demo=True,
            is_read_only=True,
        )
        Company.objects.create(
            name="Demo Oculta",
            owner=demo_owner,
            is_demo=True,
            is_read_only=True,
        )
        CourseDemoCompanyVisibility.objects.create(
            course=course,
            company=visible_demo,
            is_visible=True,
        )

        visible_ids = set(list_companies(user=student).values_list("id", flat=True))

        assert own_company.id in visible_ids
        assert visible_demo.id in visible_ids
        assert len(visible_ids) == 2
