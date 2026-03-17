import datetime
from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.companies import services as company_services
from apps.companies.models import Company
from apps.journal.models import JournalEntry
from apps.users.models import User
from tests.support.opening import create_legacy_journal_entry, seed_opening_chart


@pytest.mark.django_db
class TestOpeningGates:
    def test_journal_detail_is_blocked_until_company_has_opening(self, api_client: APIClient):
        student = User.objects.create_user(
            username="student-journal-detail-gate",
            password="x",
            role=User.Role.STUDENT,
        )
        company = Company.objects.create(name="Empresa Detalle Bloqueado", owner=student)
        entry = create_legacy_journal_entry(company=company, created_by=student)

        api_client.force_authenticate(student)
        response = api_client.get(f"/api/v1/companies/{company.id}/journal/{entry.id}/")

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_journal_reverse_is_blocked_until_company_has_opening(self, api_client: APIClient):
        student = User.objects.create_user(
            username="student-journal-reverse-gate",
            password="x",
            role=User.Role.STUDENT,
        )
        company = Company.objects.create(name="Empresa Reversa Bloqueada", owner=student)
        entry = create_legacy_journal_entry(company=company, created_by=student)

        api_client.force_authenticate(student)
        response = api_client.post(
            f"/api/v1/companies/{company.id}/journal/{entry.id}/reverse/",
            {},
            format="json",
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.parametrize(
        "path",
        [
            "/reports/journal-book/",
            "/reports/ledger/",
            "/reports/trial-balance/",
        ],
    )
    def test_reports_are_blocked_until_company_has_opening(
        self,
        api_client: APIClient,
        path: str,
    ):
        student = User.objects.create_user(
            username=f"student-report-gate-{path.split('/')[-2]}",
            password="x",
            role=User.Role.STUDENT,
        )
        company = Company.objects.create(name=f"Empresa {path}", owner=student)

        api_client.force_authenticate(student)
        response = api_client.get(f"/api/v1/companies/{company.id}{path}")

        assert response.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.parametrize(
        "path",
        [
            "/reports/journal-book.xlsx",
            "/reports/ledger.xlsx",
            "/reports/trial-balance.xlsx",
        ],
    )
    def test_report_exports_are_blocked_until_company_has_opening(
        self,
        api_client: APIClient,
        path: str,
    ):
        student = User.objects.create_user(
            username=f"student-export-gate-{path.split('/')[-1]}",
            password="x",
            role=User.Role.STUDENT,
        )
        company = Company.objects.create(name=f"Empresa Export {path}", owner=student)

        api_client.force_authenticate(student)
        with patch("apps.reports.views._ensure_excel_dependency", return_value=None):
            response = api_client.get(f"/api/v1/companies/{company.id}{path}")

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_company_with_opening_can_reverse_non_opening_entry(self, api_client: APIClient):
        student = User.objects.create_user(
            username="student-opened-reverse",
            password="x",
            role=User.Role.STUDENT,
        )
        parents = seed_opening_chart()
        company = company_services.create_company_with_optional_opening(
            name="Empresa Con Apertura y Reversa",
            owner=student,
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
        operating_account = (
            company.accounts.exclude(account__parent__full_code="3.01").get().account
        )
        manual = JournalEntry.objects.create(
            company=company,
            entry_number=2,
            date=datetime.date(2026, 3, 2),
            description="Legacy manual entry",
            source_type=JournalEntry.SourceType.MANUAL,
            created_by=student,
        )
        manual.lines.create(account=operating_account, type="DEBIT", amount="10.00")
        manual.lines.create(account=operating_account, type="CREDIT", amount="10.00")

        api_client.force_authenticate(student)
        response = api_client.post(
            f"/api/v1/companies/{company.id}/journal/{manual.id}/reverse/",
            {},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
