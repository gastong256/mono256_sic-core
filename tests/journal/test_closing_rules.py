import datetime

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.companies import services as company_services
from apps.companies.models import Company
from apps.journal.models import JournalEntry
from apps.users.models import User
from tests.support.opening import seed_opening_chart


@pytest.mark.django_db
class TestClosingRules:
    def test_opening_is_rejected_on_or_before_books_closed_until(self, api_client: APIClient):
        student = User.objects.create_user(
            username="student-closed-opening",
            password="x",
            role=User.Role.STUDENT,
        )
        parents = seed_opening_chart()
        company = Company.objects.create(
            name="Empresa Cerrada",
            owner=student,
            books_closed_until=datetime.date(2026, 3, 1),
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

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_opening_is_allowed_after_books_closed_until(self, api_client: APIClient):
        student = User.objects.create_user(
            username="student-open-after-close",
            password="x",
            role=User.Role.STUDENT,
        )
        parents = seed_opening_chart()
        company = Company.objects.create(
            name="Empresa Abierta Despues",
            owner=student,
            books_closed_until=datetime.date(2026, 3, 1),
        )

        api_client.force_authenticate(student)
        response = api_client.post(
            f"/api/v1/companies/{company.id}/opening-entry/",
            {
                "date": "2026-03-02",
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

    def test_opening_entries_cannot_be_reversed(self, api_client: APIClient):
        student = User.objects.create_user(
            username="student-no-reverse-opening",
            password="x",
            role=User.Role.STUDENT,
        )
        parents = seed_opening_chart()
        company = company_services.create_company_with_optional_opening(
            name="Empresa Sin Reversa",
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
        opening = company.journal_entries.get(source_type=JournalEntry.SourceType.OPENING)

        api_client.force_authenticate(student)
        response = api_client.post(
            f"/api/v1/companies/{company.id}/journal/{opening.id}/reverse/",
            {},
            format="json",
        )

        assert response.status_code == status.HTTP_409_CONFLICT
