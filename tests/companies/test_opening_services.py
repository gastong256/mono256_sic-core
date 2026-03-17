import datetime

import pytest
from rest_framework.exceptions import PermissionDenied, ValidationError

from config.exceptions import ConflictError
from apps.companies import services as company_services
from apps.companies.models import Company, CompanyAccount
from apps.journal.models import JournalEntry
from apps.users.models import User
from tests.support.opening import create_legacy_journal_entry, seed_opening_chart


@pytest.mark.django_db
class TestCompanyOpeningServices:
    def test_optional_opening_creates_single_capital_line_and_flags(self):
        student = User.objects.create_user(
            username="student-service-opening",
            password="x",
            role=User.Role.STUDENT,
        )
        parents = seed_opening_chart()

        company = company_services.create_company_with_optional_opening(
            name="Empresa Servicio",
            owner=student,
            opening_entry={
                "date": datetime.date(2026, 3, 1),
                "assets": [
                    {
                        "name": "Caja Principal",
                        "parent_code": parents["cash"].full_code,
                        "amount": "100.00",
                    },
                    {
                        "name": "Banco Principal",
                        "parent_code": parents["bank"].full_code,
                        "amount": "50.00",
                    },
                ],
                "liabilities": [
                    {
                        "name": "Proveedor Inicial",
                        "parent_code": parents["suppliers"].full_code,
                        "amount": "20.00",
                    }
                ],
            },
        )

        entry = JournalEntry.objects.get(company=company)
        capital_lines = entry.lines.filter(account__parent__full_code="3.01", type="CREDIT")

        assert entry.source_type == JournalEntry.SourceType.OPENING
        assert entry.entry_number == 1
        assert capital_lines.count() == 1
        assert str(capital_lines.get().amount) == "130.00"

    def test_opening_reuses_existing_company_account_with_same_parent_and_name(self):
        student = User.objects.create_user(
            username="student-reuse-opening-account",
            password="x",
            role=User.Role.STUDENT,
        )
        parents = seed_opening_chart()
        company = Company.objects.create(name="Empresa Reuso", owner=student)
        existing = parents["cash"].__class__.objects.create(
            code=".01",
            name="Caja Principal",
            parent=parents["cash"],
            type=parents["cash"].type,
            currencies=parents["cash"].currencies,
        )
        CompanyAccount.objects.create(company=company, account=existing)

        company_services.create_company_opening_entry(
            company=company,
            actor=student,
            opening_entry={
                "date": datetime.date(2026, 3, 1),
                "assets": [
                    {
                        "name": "Caja Principal",
                        "parent_code": parents["cash"].full_code,
                        "amount": "100.00",
                    }
                ],
            },
        )

        assert (
            CompanyAccount.objects.filter(company=company, account__name="Caja Principal").count()
            == 1
        )

    def test_opening_rejects_account_name_that_belongs_to_another_company(self):
        owner_a = User.objects.create_user(
            username="student-owner-a",
            password="x",
            role=User.Role.STUDENT,
        )
        owner_b = User.objects.create_user(
            username="student-owner-b",
            password="x",
            role=User.Role.STUDENT,
        )
        parents = seed_opening_chart()
        company_a = Company.objects.create(name="Empresa A", owner=owner_a)
        company_b = Company.objects.create(name="Empresa B", owner=owner_b)
        existing = parents["cash"].__class__.objects.create(
            code=".01",
            name="Caja Principal",
            parent=parents["cash"],
            type=parents["cash"].type,
            currencies=parents["cash"].currencies,
        )
        CompanyAccount.objects.create(company=company_a, account=existing)

        with pytest.raises(ValidationError):
            company_services.create_company_opening_entry(
                company=company_b,
                actor=owner_b,
                opening_entry={
                    "date": datetime.date(2026, 3, 1),
                    "assets": [
                        {
                            "name": "Caja Principal",
                            "parent_code": parents["cash"].full_code,
                            "amount": "100.00",
                        }
                    ],
                },
            )

    def test_opening_requires_owner_or_admin(self):
        teacher = User.objects.create_user(
            username="teacher-service-open-denied",
            password="x",
            role=User.Role.TEACHER,
        )
        student = User.objects.create_user(
            username="student-service-open-target",
            password="x",
            role=User.Role.STUDENT,
        )
        parents = seed_opening_chart()
        company = Company.objects.create(name="Empresa Permiso", owner=student)

        with pytest.raises(PermissionDenied):
            company_services.create_company_opening_entry(
                company=company,
                actor=teacher,
                opening_entry={
                    "date": datetime.date(2026, 3, 1),
                    "assets": [
                        {
                            "name": "Caja Principal",
                            "parent_code": parents["cash"].full_code,
                            "amount": "100.00",
                        }
                    ],
                },
            )

    def test_opening_rejects_existing_legacy_entry(self):
        student = User.objects.create_user(
            username="student-service-legacy",
            password="x",
            role=User.Role.STUDENT,
        )
        parents = seed_opening_chart()
        company = Company.objects.create(name="Empresa Legacy Servicio", owner=student)
        create_legacy_journal_entry(company=company, created_by=student)

        with pytest.raises(ConflictError):
            company_services.create_company_opening_entry(
                company=company,
                actor=student,
                opening_entry={
                    "date": datetime.date(2026, 3, 1),
                    "assets": [
                        {
                            "name": "Caja Principal",
                            "parent_code": parents["cash"].full_code,
                            "amount": "100.00",
                        }
                    ],
                },
            )
