import pytest
from rest_framework import status
from rest_framework.test import APIClient

from hordak.models import Account

from apps.companies import services as company_services
from apps.companies.models import Company, CompanyAccount
from apps.journal.models import JournalEntry
from apps.users.models import User


def _seed_opening_chart() -> dict[str, Account]:
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
    root_liabilities = Account.objects.create(
        code="2",
        name="PASIVO",
        type="LI",
        currencies=["ARS"],
    )
    parent_suppliers = Account.objects.create(
        code=".01",
        name="Proveedores",
        parent=root_liabilities,
        type="LI",
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
    return {
        "cash": parent_cash,
        "bank": parent_bank,
        "suppliers": parent_suppliers,
        "capital": parent_capital,
    }


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
        assert payload["has_opening_entry"] is False
        assert payload["accounting_ready"] is False
        assert payload["opening_entry_id"] is None
        company = Company.objects.get(pk=payload["id"])
        assert company.journal_entries.count() == 0
        assert company.accounts.count() == 0

    def test_create_company_can_post_optional_opening_entry(self, api_client: APIClient):
        student = User.objects.create_user(
            username="student-opening-company",
            password="x",
            role=User.Role.STUDENT,
        )
        parents = _seed_opening_chart()
        api_client.force_authenticate(student)

        response = api_client.post(
            "/api/v1/companies/",
            {
                "name": "Empresa Con Apertura",
                "description": "Comercio minorista simulado",
                "opening_entry": {
                    "date": "2026-03-16",
                    "inventory_kind": "INITIAL",
                    "source_ref": "APERTURA-001",
                    "assets": [
                        {
                            "name": "Caja Principal",
                            "parent_code": parents["cash"].full_code,
                            "amount": "500000.00",
                        },
                        {
                            "name": "Banco Cuenta Corriente",
                            "parent_code": parents["bank"].full_code,
                            "amount": "1500000.00",
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
        assert payload["has_opening_entry"] is True
        assert payload["accounting_ready"] is True
        assert payload["opening_entry_id"] is not None

        company = Company.objects.get(pk=payload["id"])
        company_accounts = CompanyAccount.objects.filter(company=company).select_related("account")
        assert company_accounts.count() == 3
        full_codes = sorted(account.account.full_code for account in company_accounts)
        assert full_codes[0].startswith("1.01.")
        assert full_codes[1].startswith("1.04.")
        assert full_codes[2].startswith("3.01.")

        entry = JournalEntry.objects.get(company=company)
        assert entry.entry_number == 1
        assert entry.source_type == JournalEntry.SourceType.OPENING
        assert entry.description == "s/ Inventario Inicial"
        assert entry.source_ref == "APERTURA-001"
        assert entry.lines.count() == 3
        capital_line = entry.lines.get(type="CREDIT", account__parent__full_code="3.01")
        assert str(capital_line.amount) == "2000000.00"

    def test_create_company_rolls_back_when_opening_entry_is_invalid(self, api_client: APIClient):
        student = User.objects.create_user(
            username="student-invalid-opening-company",
            password="x",
            role=User.Role.STUDENT,
        )
        _seed_opening_chart()
        api_client.force_authenticate(student)

        response = api_client.post(
            "/api/v1/companies/",
            {
                "name": "Empresa Fallida",
                "opening_entry": {
                    "date": "2026-03-16",
                    "assets": [
                        {
                            "name": "Caja Principal",
                            "parent_code": "1.01",
                            "amount": "100.00",
                        }
                    ],
                    "liabilities": [
                        {
                            "name": "Proveedor Inicial",
                            "parent_code": "2.01",
                            "amount": "100.00",
                        }
                    ],
                },
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Company.objects.filter(name="Empresa Fallida").count() == 0
        assert JournalEntry.objects.count() == 0

    def test_existing_company_can_be_opened_only_once_through_opening_endpoint(
        self, api_client: APIClient
    ):
        student = User.objects.create_user(
            username="student-open-later",
            password="x",
            role=User.Role.STUDENT,
        )
        parents = _seed_opening_chart()
        company = Company.objects.create(name="Empresa Tardia", owner=student)

        api_client.force_authenticate(student)
        response = api_client.post(
            f"/api/v1/companies/{company.id}/opening-entry/",
            {
                "date": "2026-03-01",
                "inventory_kind": "GENERAL",
                "assets": [
                    {
                        "name": "Caja Operativa",
                        "parent_code": parents["cash"].full_code,
                        "amount": "750000.00",
                    }
                ],
                "liabilities": [
                    {
                        "name": "Proveedor Inicial",
                        "parent_code": parents["suppliers"].full_code,
                        "amount": "250000.00",
                    }
                ],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        payload = response.json()
        assert payload["source_type"] == "OPENING"
        assert payload["description"] == "s/ Inventario General"

        duplicate = api_client.post(
            f"/api/v1/companies/{company.id}/opening-entry/",
            {
                "date": "2026-03-02",
                "assets": [
                    {
                        "name": "Caja Operativa 2",
                        "parent_code": parents["cash"].full_code,
                        "amount": "100.00",
                    }
                ],
            },
            format="json",
        )
        assert duplicate.status_code == status.HTTP_409_CONFLICT

    def test_company_without_opening_cannot_post_regular_journal_entries(
        self, api_client: APIClient
    ):
        student = User.objects.create_user(
            username="student-blocked-journal",
            password="x",
            role=User.Role.STUDENT,
        )
        parents = _seed_opening_chart()
        company = Company.objects.create(name="Empresa Bloqueada", owner=student)
        movement = Account.objects.create(
            code=".01",
            name="Caja Previa",
            parent=parents["cash"],
            type="AS",
            currencies=["ARS"],
        )
        CompanyAccount.objects.create(account=movement, company=company)

        api_client.force_authenticate(student)
        response = api_client.post(
            f"/api/v1/companies/{company.id}/journal/",
            {
                "date": "2026-03-16",
                "description": "Asiento regular",
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

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_company_without_opening_cannot_list_journal_entries(self, api_client: APIClient):
        student = User.objects.create_user(
            username="student-blocked-journal-list",
            password="x",
            role=User.Role.STUDENT,
        )
        company = Company.objects.create(name="Empresa Sin Diario", owner=student)

        api_client.force_authenticate(student)
        response = api_client.get(f"/api/v1/companies/{company.id}/journal/")

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_regular_journal_endpoint_rejects_opening_source_type(self, api_client: APIClient):
        student = User.objects.create_user(
            username="student-open-source-type",
            password="x",
            role=User.Role.STUDENT,
        )
        parents = _seed_opening_chart()
        company = company_services.create_company_with_optional_opening(
            name="Empresa Abierta",
            owner=student,
            opening_entry={
                "date": "2026-03-16",
                "assets": [
                    {
                        "name": "Caja Principal",
                        "parent_code": parents["cash"].full_code,
                        "amount": "100.00",
                    }
                ],
            },
        )
        movement = (
            CompanyAccount.objects.filter(company=company)
            .exclude(account__parent__full_code="3.01")
            .get()
            .account
        )

        api_client.force_authenticate(student)
        response = api_client.post(
            f"/api/v1/companies/{company.id}/journal/",
            {
                "date": "2026-03-17",
                "description": "Intento de apertura por endpoint general",
                "source_type": "OPENING",
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

        assert response.status_code == status.HTTP_400_BAD_REQUEST
