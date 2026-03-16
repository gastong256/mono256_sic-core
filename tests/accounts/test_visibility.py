import pytest
from rest_framework import status
from rest_framework.test import APIClient

from hordak.models import Account

from apps.accounts.models import TeacherAccountVisibility
from apps.accounts.selectors import get_global_chart
from apps.courses.services import create_course, enroll_student
from apps.users.models import User


@pytest.mark.django_db
class TestAccountVisibility:
    def test_student_global_chart_hides_teacher_overridden_level1_account(self):
        root = Account.objects.create(code="1", name="ACTIVO", type="AS", currencies=["ARS"])
        child = Account.objects.create(
            code=".01", name="Caja", parent=root, type="AS", currencies=["ARS"]
        )

        teacher = User.objects.create_user(username="teacher", password="x", role=User.Role.TEACHER)
        student = User.objects.create_user(username="student", password="x", role=User.Role.STUDENT)
        course = create_course(teacher=teacher, name="A")
        enroll_student(course=course, student=student)

        TeacherAccountVisibility.objects.create(teacher=teacher, account=child, is_visible=False)

        tree = get_global_chart(user=student)

        assert tree[0]["code"] == "1"
        assert tree[0]["children"] == []

    def test_visibility_bootstrap_returns_teacher_list_and_chart(self, api_client: APIClient):
        root = Account.objects.create(code="1", name="ACTIVO", type="AS", currencies=["ARS"])
        child = Account.objects.create(
            code=".01", name="Caja", parent=root, type="AS", currencies=["ARS"]
        )
        teacher = User.objects.create_user(
            username="teacher-bootstrap", password="x", role=User.Role.TEACHER
        )
        admin = User.objects.create_user(username="admin-bootstrap", password="x", role=User.Role.ADMIN)
        TeacherAccountVisibility.objects.create(teacher=teacher, account=child, is_visible=False)

        api_client.force_authenticate(admin)
        response = api_client.get(f"/api/v1/accounts/visibility/bootstrap/?teacher_id={teacher.id}")

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["selected_teacher_id"] == teacher.id
        assert payload["teachers"][0]["id"] == teacher.id
        assert payload["chart"][0]["children"][0]["is_visible"] is False
