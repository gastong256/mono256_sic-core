import datetime

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.companies import services as company_services
from apps.companies.models import Company
from apps.courses.models import CourseSharedCompanyVisibility
from apps.courses.services import create_course, enroll_student
from apps.users.models import User
from tests.support.opening import seed_opening_chart


@pytest.mark.django_db
class TestCourseSharedCompanyReadOnlyAccess:
    def test_student_list_includes_visible_shared_company_with_read_only_access(
        self,
        api_client: APIClient,
    ):
        teacher = User.objects.create_user(
            username="teacher-shared-list",
            password="x",
            role=User.Role.TEACHER,
        )
        student = User.objects.create_user(
            username="student-shared-list",
            password="x",
            role=User.Role.STUDENT,
        )
        course = create_course(teacher=teacher, name="Curso Shared List")
        enroll_student(course=course, student=student)
        shared_company = Company.objects.create(name="Empresa Compartida Curso", owner=teacher)
        CourseSharedCompanyVisibility.objects.create(
            course=course,
            company=shared_company,
            is_visible=True,
        )

        api_client.force_authenticate(student)
        response = api_client.get("/api/v1/companies/?all=true&summary=selector")

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["results"] == [
            {
                "id": shared_company.id,
                "name": shared_company.name,
                "owner_username": teacher.username,
                "is_demo": False,
                "is_read_only": False,
                "is_published": True,
                "demo_slug": "",
                "viewer_can_write": False,
                "has_opening_entry": False,
                "accounting_ready": False,
            }
        ]

    def test_student_can_read_but_cannot_write_shared_company(
        self,
        api_client: APIClient,
    ):
        teacher = User.objects.create_user(
            username="teacher-shared-readonly",
            password="x",
            role=User.Role.TEACHER,
        )
        student = User.objects.create_user(
            username="student-shared-readonly",
            password="x",
            role=User.Role.STUDENT,
        )
        course = create_course(teacher=teacher, name="Curso Shared Read Only")
        enroll_student(course=course, student=student)
        parents = seed_opening_chart()
        shared_company = company_services.create_company_with_optional_opening(
            name="Empresa Compartida Operativa",
            owner=teacher,
            opening_entry={
                "date": datetime.date(2026, 3, 16),
                "assets": [
                    {
                        "name": "Caja Principal",
                        "parent_code": parents["cash"].full_code,
                        "amount": "1000.00",
                    }
                ],
            },
        )
        CourseSharedCompanyVisibility.objects.create(
            course=course,
            company=shared_company,
            is_visible=True,
        )
        cash_account = shared_company.accounts.get(
            account__parent__full_code=parents["cash"].full_code
        )
        capital_account = shared_company.accounts.get(
            account__parent__full_code=parents["capital"].full_code
        )

        api_client.force_authenticate(student)

        detail_response = api_client.get(f"/api/v1/companies/{shared_company.id}/")
        assert detail_response.status_code == status.HTTP_200_OK
        assert detail_response.json()["viewer_can_write"] is False

        update_response = api_client.patch(
            f"/api/v1/companies/{shared_company.id}/",
            {"name": "Intento Edicion Alumno"},
            format="json",
        )
        assert update_response.status_code == status.HTTP_409_CONFLICT

        account_response = api_client.post(
            f"/api/v1/accounts/company/{shared_company.id}/",
            {
                "name": "Nueva Cuenta Bloqueada",
                "code": "1.01.02",
                "parent_id": parents["cash"].id,
            },
            format="json",
        )
        assert account_response.status_code == status.HTTP_409_CONFLICT

        journal_response = api_client.post(
            f"/api/v1/companies/{shared_company.id}/journal/",
            {
                "date": "2026-03-17",
                "description": "Intento escritura compartida",
                "lines": [
                    {
                        "account_id": cash_account.account_id,
                        "type": "DEBIT",
                        "amount": "100.00",
                    },
                    {
                        "account_id": capital_account.account_id,
                        "type": "CREDIT",
                        "amount": "100.00",
                    },
                ],
            },
            format="json",
        )
        assert journal_response.status_code == status.HTTP_409_CONFLICT
