import pytest
from rest_framework import status
from rest_framework.test import APIClient

from hordak.models import Account

from apps.accounts.models import TeacherAccountVisibility
from apps.companies.models import Company
from apps.courses.services import create_course, enroll_student
from apps.users.models import User
from tests.support.opening import seed_opening_chart


@pytest.mark.django_db
class TestCompanyOpeningPermissions:
    def test_owner_can_open_existing_company(self, api_client: APIClient):
        student = User.objects.create_user(
            username="student-owner-open",
            password="x",
            role=User.Role.STUDENT,
        )
        company = Company.objects.create(name="Empresa Propia", owner=student)
        parents = seed_opening_chart()

        api_client.force_authenticate(student)
        response = api_client.post(
            f"/api/v1/companies/{company.id}/opening-entry/",
            {
                "date": "2026-03-01",
                "assets": [
                    {
                        "name": "Caja Principal",
                        "parent_code": parents["cash"].full_code,
                        "amount": "100.00",
                    }
                ],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_admin_can_open_existing_foreign_company(self, api_client: APIClient):
        admin = User.objects.create_user(
            username="admin-open-foreign",
            password="x",
            role=User.Role.ADMIN,
        )
        student = User.objects.create_user(
            username="student-open-foreign",
            password="x",
            role=User.Role.STUDENT,
        )
        company = Company.objects.create(name="Empresa Ajena", owner=student)
        parents = seed_opening_chart()

        api_client.force_authenticate(admin)
        response = api_client.post(
            f"/api/v1/companies/{company.id}/opening-entry/",
            {
                "date": "2026-03-01",
                "assets": [
                    {
                        "name": "Caja Principal",
                        "parent_code": parents["cash"].full_code,
                        "amount": "100.00",
                    }
                ],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_student_cannot_open_another_students_company(self, api_client: APIClient):
        owner = User.objects.create_user(
            username="student-owner-locked",
            password="x",
            role=User.Role.STUDENT,
        )
        outsider = User.objects.create_user(
            username="student-outsider-locked",
            password="x",
            role=User.Role.STUDENT,
        )
        company = Company.objects.create(name="Empresa Bloqueada", owner=owner)
        parents = seed_opening_chart()

        api_client.force_authenticate(outsider)
        response = api_client.post(
            f"/api/v1/companies/{company.id}/opening-entry/",
            {
                "date": "2026-03-01",
                "assets": [
                    {
                        "name": "Caja Principal",
                        "parent_code": parents["cash"].full_code,
                        "amount": "100.00",
                    }
                ],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_student_cannot_open_with_hidden_collective(self, api_client: APIClient):
        teacher = User.objects.create_user(
            username="teacher-hidden-opening",
            password="x",
            role=User.Role.TEACHER,
        )
        student = User.objects.create_user(
            username="student-hidden-opening",
            password="x",
            role=User.Role.STUDENT,
        )
        course = create_course(teacher=teacher, name="Apertura")
        enroll_student(course=course, student=student)
        company = Company.objects.create(name="Empresa Oculta", owner=student)
        parents = seed_opening_chart()
        hidden_collective = Account.objects.get(full_code=parents["cash"].full_code)
        TeacherAccountVisibility.objects.create(
            teacher=teacher,
            account=hidden_collective,
            is_visible=False,
        )

        api_client.force_authenticate(student)
        response = api_client.post(
            f"/api/v1/companies/{company.id}/opening-entry/",
            {
                "date": "2026-03-01",
                "assets": [
                    {
                        "name": "Caja Principal",
                        "parent_code": parents["cash"].full_code,
                        "amount": "100.00",
                    }
                ],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
