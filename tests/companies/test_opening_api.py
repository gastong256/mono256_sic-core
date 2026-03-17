import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.companies.models import Company
from apps.courses.services import create_course, enroll_student
from apps.journal.models import JournalEntry
from apps.users.models import User
from tests.support.opening import create_legacy_journal_entry, seed_opening_chart


@pytest.mark.django_db
class TestCompanyOpeningApi:
    def test_create_company_opening_with_assets_and_liabilities_computes_capital(
        self,
        api_client: APIClient,
    ):
        student = User.objects.create_user(
            username="student-opening-assets-liabilities",
            password="x",
            role=User.Role.STUDENT,
        )
        parents = seed_opening_chart()

        api_client.force_authenticate(student)
        response = api_client.post(
            "/api/v1/companies/",
            {
                "name": "Empresa Patrimonial",
                "opening_entry": {
                    "date": "2026-03-16",
                    "inventory_kind": "INITIAL",
                    "assets": [
                        {
                            "name": "Caja Principal",
                            "parent_code": parents["cash"].full_code,
                            "amount": "1000.00",
                        },
                        {
                            "name": "Banco Principal",
                            "parent_code": parents["bank"].full_code,
                            "amount": "500.00",
                        },
                        {
                            "name": "Muebles de Oficina",
                            "parent_code": parents["furniture"].full_code,
                            "amount": "500.00",
                        },
                    ],
                    "liabilities": [
                        {
                            "name": "Proveedor Inicial",
                            "parent_code": parents["suppliers"].full_code,
                            "amount": "200.00",
                        }
                    ],
                },
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        company = Company.objects.get(pk=response.json()["id"])
        entry = JournalEntry.objects.get(company=company)
        capital_line = entry.lines.get(type="CREDIT", account__parent__full_code="3.01")
        assert str(capital_line.amount) == "1800.00"
        assert entry.lines.count() == 5

    def test_existing_company_opening_is_rejected_if_legacy_entry_exists(
        self, api_client: APIClient
    ):
        student = User.objects.create_user(
            username="student-legacy-opening",
            password="x",
            role=User.Role.STUDENT,
        )
        parents = seed_opening_chart()
        company = Company.objects.create(name="Empresa Legacy", owner=student)
        create_legacy_journal_entry(company=company, created_by=student)

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

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_existing_company_opening_is_rejected_for_read_only_company(
        self, api_client: APIClient
    ):
        admin = User.objects.create_user(
            username="admin-read-only-opening",
            password="x",
            role=User.Role.ADMIN,
        )
        parents = seed_opening_chart()
        company = Company.objects.create(
            name="Empresa Solo Lectura",
            owner=admin,
            is_read_only=True,
        )

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

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_company_becomes_operational_after_opening(self, api_client: APIClient):
        student = User.objects.create_user(
            username="student-open-and-operate",
            password="x",
            role=User.Role.STUDENT,
        )
        parents = seed_opening_chart()
        company = Company.objects.create(name="Empresa Operativa", owner=student)

        api_client.force_authenticate(student)
        open_response = api_client.post(
            f"/api/v1/companies/{company.id}/opening-entry/",
            {
                "date": "2026-03-01",
                "inventory_kind": "GENERAL",
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

        assert open_response.status_code == status.HTTP_201_CREATED
        journal_response = api_client.get(f"/api/v1/companies/{company.id}/journal/")
        report_response = api_client.get(f"/api/v1/companies/{company.id}/reports/trial-balance/")

        assert journal_response.status_code == status.HTTP_200_OK
        assert report_response.status_code == status.HTTP_200_OK
        assert Company.objects.get(pk=company.id).journal_entries.count() == 1

    def test_teacher_cannot_open_student_company_even_with_course_access(
        self, api_client: APIClient
    ):
        teacher = User.objects.create_user(
            username="teacher-open-foreign-company",
            password="x",
            role=User.Role.TEACHER,
        )
        student = User.objects.create_user(
            username="student-open-foreign-company",
            password="x",
            role=User.Role.STUDENT,
        )
        course = create_course(teacher=teacher, name="Contabilidad I")
        enroll_student(course=course, student=student)
        company = Company.objects.create(name="Empresa Alumno", owner=student)
        parents = seed_opening_chart()

        api_client.force_authenticate(teacher)
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
