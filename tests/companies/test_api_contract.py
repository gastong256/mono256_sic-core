import pytest
from rest_framework import status
from rest_framework.test import APIClient

from hordak.models import Account

from apps.companies.models import Company, CompanyAccount
from apps.journal.models import JournalEntry
from apps.users.models import User


@pytest.mark.django_db
class TestCompanyApiContract:
    def test_list_companies_supports_all_and_selector_summary(self, api_client: APIClient):
        student = User.objects.create_user(
            username="student-companies",
            password="x",
            role=User.Role.STUDENT,
        )
        Company.objects.create(name="Empresa Uno", owner=student)
        Company.objects.create(name="Empresa Dos", owner=student)

        api_client.force_authenticate(student)
        response = api_client.get("/api/v1/companies/?all=true&summary=selector")

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["count"] == 2
        assert payload["next"] is None
        assert payload["previous"] is None
        assert sorted(item["name"] for item in payload["results"]) == [
            "Empresa Dos",
            "Empresa Uno",
        ]

    def test_create_company_without_opening_keeps_current_behavior(self, api_client: APIClient):
        student = User.objects.create_user(
            username="student-create-company",
            password="x",
            role=User.Role.STUDENT,
        )
        api_client.force_authenticate(student)

        response = api_client.post(
            "/api/v1/companies/",
            {
                "name": "Empresa Sin Apertura",
                "description": "Empresa ya en marcha",
                "tax_id": "30-12345678-9",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        payload = response.json()
        assert payload["name"] == "Empresa Sin Apertura"
        assert payload["description"] == "Empresa ya en marcha"
        company = Company.objects.get(pk=payload["id"])
        assert company.journal_entries.count() == 0
        assert company.accounts.count() == 0

    def test_create_company_can_post_optional_opening_entry(self, api_client: APIClient):
        student = User.objects.create_user(
            username="student-opening-company",
            password="x",
            role=User.Role.STUDENT,
        )
        root_assets = Account.objects.create(code="1", name="ACTIVO", type="AS", currencies=["ARS"])
        parent_cash = Account.objects.create(
            code=".01",
            name="Caja",
            parent=root_assets,
            type="AS",
            currencies=["ARS"],
        )
        parent_bank = Account.objects.create(
            code=".04",
            name="Bancos",
            parent=root_assets,
            type="AS",
            currencies=["ARS"],
        )
        root_equity = Account.objects.create(
            code="3",
            name="PATRIMONIO NETO",
            type="EQ",
            currencies=["ARS"],
        )
        parent_capital = Account.objects.create(
            code=".01",
            name="Capital",
            parent=root_equity,
            type="EQ",
            currencies=["ARS"],
        )
        api_client.force_authenticate(student)

        response = api_client.post(
            "/api/v1/companies/",
            {
                "name": "Empresa Con Apertura",
                "description": "Comercio minorista simulado",
                "opening_entry": {
                    "date": "2026-03-16",
                    "description": "Aporte inicial de capital",
                    "source_ref": "APERTURA-001",
                    "lines": [
                        {
                            "code": "1.01.01",
                            "name": "Caja Principal",
                            "parent_code": parent_cash.full_code,
                            "type": "DEBIT",
                            "amount": "500000.00",
                        },
                        {
                            "code": "1.04.01",
                            "name": "Banco Cuenta Corriente",
                            "parent_code": parent_bank.full_code,
                            "type": "DEBIT",
                            "amount": "1500000.00",
                        },
                        {
                            "code": "3.01.01",
                            "name": "Capital Social",
                            "parent_code": parent_capital.full_code,
                            "type": "CREDIT",
                            "amount": "2000000.00",
                        },
                    ],
                },
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        payload = response.json()
        assert payload["name"] == "Empresa Con Apertura"
        assert payload["description"] == "Comercio minorista simulado"
        assert payload["account_count"] == 3

        company = Company.objects.get(pk=payload["id"])
        company_accounts = CompanyAccount.objects.filter(company=company).select_related("account")
        assert company_accounts.count() == 3
        assert sorted(account.account.full_code for account in company_accounts) == [
            "1.01.01",
            "1.04.01",
            "3.01.01",
        ]

        entry = JournalEntry.objects.get(company=company)
        assert entry.entry_number == 1
        assert entry.description == "Aporte inicial de capital"
        assert entry.source_ref == "APERTURA-001"
        assert entry.lines.count() == 3

    def test_create_company_rolls_back_when_opening_entry_is_invalid(self, api_client: APIClient):
        student = User.objects.create_user(
            username="student-invalid-opening-company",
            password="x",
            role=User.Role.STUDENT,
        )
        root_assets = Account.objects.create(code="1", name="ACTIVO", type="AS", currencies=["ARS"])
        Account.objects.create(
            code=".01",
            name="Caja",
            parent=root_assets,
            type="AS",
            currencies=["ARS"],
        )
        api_client.force_authenticate(student)

        response = api_client.post(
            "/api/v1/companies/",
            {
                "name": "Empresa Fallida",
                "opening_entry": {
                    "date": "2026-03-16",
                    "description": "Apertura inválida",
                    "lines": [
                        {
                            "code": "1.01.01",
                            "name": "Caja Principal",
                            "parent_code": "1.01",
                            "type": "DEBIT",
                            "amount": "100.00",
                        },
                        {
                            "code": "3.01.01",
                            "name": "Capital Social",
                            "parent_code": "3.01",
                            "type": "CREDIT",
                            "amount": "100.00",
                        },
                    ],
                },
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Company.objects.filter(name="Empresa Fallida").count() == 0
        assert JournalEntry.objects.count() == 0
