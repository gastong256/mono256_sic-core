import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.companies.models import Company, CompanyAccount
from apps.courses.models import CourseDemoCompanyVisibility
from apps.courses.services import create_course, enroll_student
from apps.users.models import User
from hordak.models import Account


@pytest.mark.django_db
class TestDemoCompanyAccessAndReadOnly:
    def test_student_list_includes_visible_demo_company_with_flags(
        self,
        api_client: APIClient,
    ):
        demo_owner = User.objects.create_user(
            username="demo-owner",
            password="x",
            role=User.Role.ADMIN,
        )
        teacher = User.objects.create_user(
            username="demo-teacher",
            password="x",
            role=User.Role.TEACHER,
        )
        student = User.objects.create_user(
            username="demo-student",
            password="x",
            role=User.Role.STUDENT,
        )
        course = create_course(teacher=teacher, name="Curso Demo")
        enroll_student(course=course, student=student)
        demo_company = Company.objects.create(
            name="Empresa Demo",
            owner=demo_owner,
            is_demo=True,
            is_read_only=True,
        )
        CourseDemoCompanyVisibility.objects.create(
            course=course,
            company=demo_company,
            is_visible=True,
        )

        api_client.force_authenticate(student)
        response = api_client.get("/api/v1/companies/?all=true&summary=selector")

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["count"] == 1
        assert payload["results"] == [
            {
                "id": demo_company.id,
                "name": demo_company.name,
                "owner_username": demo_owner.username,
                "is_demo": True,
                "is_read_only": True,
            }
        ]

    def test_student_without_course_cannot_access_demo_company(self, api_client: APIClient):
        demo_owner = User.objects.create_user(
            username="demo-owner-no-course",
            password="x",
            role=User.Role.ADMIN,
        )
        student = User.objects.create_user(
            username="demo-student-no-course",
            password="x",
            role=User.Role.STUDENT,
        )
        demo_company = Company.objects.create(
            name="Empresa Demo Oculta",
            owner=demo_owner,
            is_demo=True,
            is_read_only=True,
        )

        api_client.force_authenticate(student)
        response = api_client.get(f"/api/v1/companies/{demo_company.id}/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_teacher_and_admin_always_see_demo_company(self, api_client: APIClient):
        demo_owner = User.objects.create_user(
            username="demo-owner-global",
            password="x",
            role=User.Role.ADMIN,
        )
        teacher = User.objects.create_user(
            username="demo-teacher-global",
            password="x",
            role=User.Role.TEACHER,
        )
        admin = User.objects.create_user(
            username="demo-admin-global",
            password="x",
            role=User.Role.ADMIN,
        )
        demo_company = Company.objects.create(
            name="Empresa Demo Global",
            owner=demo_owner,
            is_demo=True,
            is_read_only=True,
        )

        api_client.force_authenticate(teacher)
        teacher_response = api_client.get("/api/v1/companies/?all=true&summary=selector")
        assert teacher_response.status_code == status.HTTP_200_OK
        assert teacher_response.json()["results"][0]["id"] == demo_company.id

        api_client.force_authenticate(admin)
        admin_response = api_client.get(f"/api/v1/companies/{demo_company.id}/")
        assert admin_response.status_code == status.HTTP_200_OK
        assert admin_response.json()["is_demo"] is True
        assert admin_response.json()["is_read_only"] is True

    def test_demo_company_blocks_company_account_and_journal_writes(
        self,
        api_client: APIClient,
    ):
        teacher = User.objects.create_user(
            username="demo-readonly-teacher",
            password="x",
            role=User.Role.TEACHER,
        )
        demo_company = Company.objects.create(
            name="Empresa Demo Read Only",
            owner=teacher,
            is_demo=True,
            is_read_only=True,
        )
        root = Account.objects.create(code="1", name="ACTIVO", type="AS", currencies=["ARS"])
        parent = Account.objects.create(
            code=".01",
            name="Caja",
            parent=root,
            type="AS",
            currencies=["ARS"],
        )
        movement = Account.objects.create(
            code=".01",
            name="Caja Principal",
            parent=parent,
            type="AS",
            currencies=["ARS"],
        )
        CompanyAccount.objects.create(account=movement, company=demo_company)

        api_client.force_authenticate(teacher)

        update_response = api_client.patch(
            f"/api/v1/companies/{demo_company.id}/",
            {"name": "Empresa Demo Editada"},
            format="json",
        )
        assert update_response.status_code == status.HTTP_409_CONFLICT

        delete_response = api_client.delete(f"/api/v1/companies/{demo_company.id}/")
        assert delete_response.status_code == status.HTTP_409_CONFLICT

        account_response = api_client.post(
            f"/api/v1/accounts/company/{demo_company.id}/",
            {
                "name": "Nueva Cuenta",
                "code": "1.01.02",
                "parent_id": parent.id,
            },
            format="json",
        )
        assert account_response.status_code == status.HTTP_409_CONFLICT

        journal_response = api_client.post(
            f"/api/v1/companies/{demo_company.id}/journal/",
            {
                "date": "2026-03-16",
                "description": "Intento de escritura demo",
                "lines": [
                    {
                        "account_id": movement.id,
                        "type": "DEBIT",
                        "amount": "100.00",
                    },
                    {
                        "account_id": movement.id,
                        "type": "CREDIT",
                        "amount": "100.00",
                    },
                ],
            },
            format="json",
        )
        assert journal_response.status_code == status.HTTP_409_CONFLICT
