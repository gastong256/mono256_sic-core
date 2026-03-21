import datetime

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from hordak.models import Account

from apps.accounts import services as account_services
from apps.companies import services as company_services
from apps.companies.models import Company, CompanyAccount
from apps.journal import services as journal_services
from apps.journal.models import JournalEntry
from apps.users.models import User


def _parent(full_code: str) -> Account:
    return Account.objects.get(full_code=full_code)


def _movement_account(*, company: Company, parent_code: str, name: str) -> Account:
    return CompanyAccount.objects.get(
        company=company,
        account__parent__full_code=parent_code,
        account__name=name,
    ).account


def _open_company(*, owner: User, name: str = "Empresa Cierre") -> Company:
    return company_services.create_company_with_optional_opening(
        name=name,
        owner=owner,
        opening_entry={
            "date": datetime.date(2026, 1, 1),
            "assets": [
                {
                    "name": "Caja Principal",
                    "parent_code": "1.01",
                    "amount": "1000.00",
                },
                {
                    "name": "Mercaderías Iniciales",
                    "parent_code": "1.09",
                    "amount": "500.00",
                },
            ],
            "liabilities": [
                {
                    "name": "Proveedor Inicial",
                    "parent_code": "2.01",
                    "amount": "200.00",
                }
            ],
        },
    )


@pytest.mark.django_db
class TestSimplifiedClosingApi:
    def setup_method(self):
        call_command("load_chart_of_accounts")

    def test_preview_and_execute_simplified_closing(self, api_client: APIClient):
        student = User.objects.create_user(
            username="student-closing-basic",
            password="x",
            role=User.Role.STUDENT,
        )
        api_client.force_authenticate(student)
        company = _open_company(owner=student)

        sales_account = account_services.create_account(
            company=company,
            actor=student,
            name="Ventas Mostrador",
            code="5.01.01",
            parent_id=_parent("5.01").id,
        )
        expense_account = account_services.create_account(
            company=company,
            actor=student,
            name="Gastos Generales Administración",
            code="4.09.01",
            parent_id=_parent("4.09").id,
        )
        cash_account = _movement_account(company=company, parent_code="1.01", name="Caja Principal")

        journal_services.create_journal_entry(
            company=company,
            created_by=student,
            date=datetime.date(2026, 6, 1),
            description="Venta contado",
            source_type=JournalEntry.SourceType.MANUAL,
            lines=[
                {
                    "account_id": cash_account.id,
                    "type": "DEBIT",
                    "amount": "300.00",
                },
                {
                    "account_id": sales_account.id,
                    "type": "CREDIT",
                    "amount": "300.00",
                },
            ],
        )
        journal_services.create_journal_entry(
            company=company,
            created_by=student,
            date=datetime.date(2026, 6, 2),
            description="Pago de gasto",
            source_type=JournalEntry.SourceType.MANUAL,
            lines=[
                {
                    "account_id": expense_account.id,
                    "type": "DEBIT",
                    "amount": "50.00",
                },
                {
                    "account_id": cash_account.id,
                    "type": "CREDIT",
                    "amount": "50.00",
                },
            ],
        )

        payload = {
            "closing_date": "2026-12-31",
            "reopening_date": "2027-01-01",
        }
        preview = api_client.post(
            f"/api/v1/companies/{company.id}/closing/preview/",
            payload,
            format="json",
        )

        assert preview.status_code == 200, preview.data
        assert preview.data["active_exercise"]["opening_source_type"] == "OPENING"
        assert preview.data["balance_sheet"]["equation"]["is_balanced"] is True
        assert preview.data["income_statement"]["net_result"]["amount"] == "250.00"
        assert preview.data["result_summary"]["total_positive"] == "300.00"
        assert preview.data["result_summary"]["total_negative"] == "50.00"
        assert preview.data["result_summary"]["net_result"] == "250.00"
        assert len(preview.data["entries"]["result_closing"]) == 2
        assert (
            preview.data["entries"]["patrimonial_closing"]["source_type"] == "PATRIMONIAL_CLOSING"
        )
        assert preview.data["entries"]["reopening"]["source_type"] == "REOPENING"

        execute = api_client.post(
            f"/api/v1/companies/{company.id}/closing/execute/",
            payload,
            format="json",
        )

        assert execute.status_code == 200, execute.data
        assert execute.data["snapshot_id"] is not None
        assert len(execute.data["created_entries"]) == 4

        company.refresh_from_db()
        assert company.books_closed_until == datetime.date(2026, 12, 31)
        assert company.journal_entries.filter(source_type="RESULT_CLOSING").count() == 2
        assert company.journal_entries.filter(source_type="PATRIMONIAL_CLOSING").count() == 1
        assert company.journal_entries.filter(source_type="REOPENING").count() == 1

        latest_snapshot = api_client.get(f"/api/v1/companies/{company.id}/closing/latest-snapshot/")
        assert latest_snapshot.status_code == 200
        assert latest_snapshot.data["balance_sheet"]["equation"]["is_balanced"] is True
        assert latest_snapshot.data["income_statement"]["net_result"]["amount"] == "250.00"

        blocked = api_client.post(
            f"/api/v1/companies/{company.id}/journal/",
            {
                "date": "2026-12-31",
                "description": "Asiento bloqueado",
                "source_type": "MANUAL",
                "lines": [
                    {"account_id": cash_account.id, "type": "DEBIT", "amount": "10.00"},
                    {"account_id": sales_account.id, "type": "CREDIT", "amount": "10.00"},
                ],
            },
            format="json",
        )
        assert blocked.status_code == 409

    def test_execute_adjustments_uses_aggregated_cash_and_inventory_and_creates_support_accounts(
        self, api_client: APIClient
    ):
        student = User.objects.create_user(
            username="student-closing-adjustments",
            password="x",
            role=User.Role.STUDENT,
        )
        api_client.force_authenticate(student)
        company = _open_company(owner=student, name="Empresa Ajustes")

        response = api_client.post(
            f"/api/v1/companies/{company.id}/closing/execute/",
            {
                "closing_date": "2026-12-31",
                "reopening_date": "2027-01-01",
                "cash_actual": "1100.00",
                "inventory_actual": "450.00",
            },
            format="json",
        )

        assert response.status_code == 200, response.data
        assert company.journal_entries.filter(source_type="ADJUSTMENT").count() == 2
        assert CompanyAccount.objects.filter(
            company=company,
            account__parent__full_code="5.06",
            account__name="Sobrante de Caja",
        ).exists()
        assert CompanyAccount.objects.filter(
            company=company,
            account__parent__full_code="4.13",
            account__name="Faltante de Mercaderías",
        ).exists()
        assert CompanyAccount.objects.filter(
            company=company,
            account__parent__full_code="1.01",
            account__name="Caja",
        ).exists()
        assert CompanyAccount.objects.filter(
            company=company,
            account__parent__full_code="1.09",
            account__name="Mercaderías",
        ).exists()

    def test_teacher_cannot_preview_or_execute_closing_for_student_company(
        self, api_client: APIClient
    ):
        teacher = User.objects.create_user(
            username="teacher-closing-denied",
            password="x",
            role=User.Role.TEACHER,
        )
        student = User.objects.create_user(
            username="student-closing-target",
            password="x",
            role=User.Role.STUDENT,
        )
        company = _open_company(owner=student, name="Empresa Permiso Cierre")
        api_client.force_authenticate(teacher)

        preview = api_client.post(
            f"/api/v1/companies/{company.id}/closing/preview/",
            {
                "closing_date": "2026-12-31",
                "reopening_date": "2027-01-01",
            },
            format="json",
        )
        execute = api_client.post(
            f"/api/v1/companies/{company.id}/closing/execute/",
            {
                "closing_date": "2026-12-31",
                "reopening_date": "2027-01-01",
            },
            format="json",
        )

        assert preview.status_code == 403
        assert execute.status_code == 403

    def test_closing_is_rejected_when_later_entries_already_exist(self, api_client: APIClient):
        student = User.objects.create_user(
            username="student-closing-later-entry",
            password="x",
            role=User.Role.STUDENT,
        )
        api_client.force_authenticate(student)
        company = _open_company(owner=student, name="Empresa Con Futuro")
        cash_account = _movement_account(company=company, parent_code="1.01", name="Caja Principal")
        capital_account = _movement_account(company=company, parent_code="3.01", name="Capital")

        journal_services.create_journal_entry(
            company=company,
            created_by=student,
            date=datetime.date(2027, 1, 10),
            description="Asiento futuro",
            source_type=JournalEntry.SourceType.MANUAL,
            lines=[
                {"account_id": cash_account.id, "type": "DEBIT", "amount": "10.00"},
                {"account_id": capital_account.id, "type": "CREDIT", "amount": "10.00"},
            ],
        )

        response = api_client.post(
            f"/api/v1/companies/{company.id}/closing/execute/",
            {
                "closing_date": "2026-12-31",
                "reopening_date": "2027-01-01",
            },
            format="json",
        )

        assert response.status_code == 409

    def test_closing_state_reports_latest_entries(self, api_client: APIClient):
        student = User.objects.create_user(
            username="student-closing-state",
            password="x",
            role=User.Role.STUDENT,
        )
        api_client.force_authenticate(student)
        company = _open_company(owner=student, name="Empresa Estado Cierre")

        execute = api_client.post(
            f"/api/v1/companies/{company.id}/closing/execute/",
            {
                "closing_date": "2026-12-31",
                "reopening_date": "2027-01-01",
            },
            format="json",
        )
        assert execute.status_code == 200, execute.data

        state = api_client.get(f"/api/v1/companies/{company.id}/closing/state/")
        assert state.status_code == 200
        assert state.data["books_closed_until"] == "2026-12-31"
        assert state.data["last_patrimonial_closing_entry_id"] is not None
        assert state.data["last_reopening_entry_id"] is not None
        assert state.data["current_exercise"]["opening_source_type"] == "REOPENING"

    def test_current_book_balances_endpoint_returns_cash_and_inventory_balances(
        self, api_client: APIClient
    ):
        student = User.objects.create_user(
            username="student-current-balances",
            password="x",
            role=User.Role.STUDENT,
        )
        api_client.force_authenticate(student)
        company = _open_company(owner=student, name="Empresa Saldos Actuales")

        sales_account = account_services.create_account(
            company=company,
            actor=student,
            name="Ventas Mostrador Saldos",
            code="5.01.02",
            parent_id=_parent("5.01").id,
        )
        cash_account = _movement_account(company=company, parent_code="1.01", name="Caja Principal")
        inventory_account = _movement_account(
            company=company,
            parent_code="1.09",
            name="Mercaderías Iniciales",
        )
        supplier_account = _movement_account(
            company=company,
            parent_code="2.01",
            name="Proveedor Inicial",
        )

        journal_services.create_journal_entry(
            company=company,
            created_by=student,
            date=datetime.date(2026, 6, 1),
            description="Venta contado para saldos",
            source_type=JournalEntry.SourceType.MANUAL,
            lines=[
                {"account_id": cash_account.id, "type": "DEBIT", "amount": "300.00"},
                {"account_id": sales_account.id, "type": "CREDIT", "amount": "300.00"},
            ],
        )
        journal_services.create_journal_entry(
            company=company,
            created_by=student,
            date=datetime.date(2026, 6, 2),
            description="Compra mercaderías para saldos",
            source_type=JournalEntry.SourceType.MANUAL,
            lines=[
                {"account_id": inventory_account.id, "type": "DEBIT", "amount": "200.00"},
                {"account_id": supplier_account.id, "type": "CREDIT", "amount": "200.00"},
            ],
        )

        response = api_client.get(f"/api/v1/companies/{company.id}/closing/current-balances/")

        assert response.status_code == 200, response.data
        assert response.data["cash"]["parent_code"] == "1.01"
        assert response.data["cash"]["book_balance"] == "1300.00"
        assert response.data["inventory"]["parent_code"] == "1.09"
        assert response.data["inventory"]["book_balance"] == "700.00"

        response_as_of_june_1 = api_client.get(
            f"/api/v1/companies/{company.id}/closing/current-balances/?date_to=2026-06-01"
        )

        assert response_as_of_june_1.status_code == 200, response_as_of_june_1.data
        assert response_as_of_june_1.data["as_of_date"] == "2026-06-01"
        assert response_as_of_june_1.data["cash"]["book_balance"] == "1300.00"
        assert response_as_of_june_1.data["inventory"]["book_balance"] == "500.00"

    def test_logical_exercises_endpoint_lists_closed_and_open_cycles(self, api_client: APIClient):
        student = User.objects.create_user(
            username="student-logical-exercises",
            password="x",
            role=User.Role.STUDENT,
        )
        api_client.force_authenticate(student)
        company = _open_company(owner=student, name="Empresa Ejercicios Lógicos")

        execute = api_client.post(
            f"/api/v1/companies/{company.id}/closing/execute/",
            {
                "closing_date": "2026-12-31",
                "reopening_date": "2027-01-01",
            },
            format="json",
        )
        assert execute.status_code == 200, execute.data

        response = api_client.get(f"/api/v1/companies/{company.id}/logical-exercises/")
        assert response.status_code == 200
        assert response.data["current_exercise_id"] is not None
        assert len(response.data["exercises"]) == 2
        assert response.data["exercises"][0]["status"] == "closed"
        assert response.data["exercises"][0]["snapshot_id"] == execute.data["snapshot_id"]
        assert response.data["exercises"][1]["status"] == "open"

    def test_closing_snapshot_can_be_retrieved_by_id(self, api_client: APIClient):
        student = User.objects.create_user(
            username="student-snapshot-detail",
            password="x",
            role=User.Role.STUDENT,
        )
        api_client.force_authenticate(student)
        company = _open_company(owner=student, name="Empresa Snapshot Detail")

        execute = api_client.post(
            f"/api/v1/companies/{company.id}/closing/execute/",
            {
                "closing_date": "2026-12-31",
                "reopening_date": "2027-01-01",
            },
            format="json",
        )
        assert execute.status_code == 200, execute.data

        response = api_client.get(
            f"/api/v1/companies/{company.id}/closing/snapshots/{execute.data['snapshot_id']}/"
        )
        assert response.status_code == 200
        assert response.data["id"] == execute.data["snapshot_id"]
        assert response.data["patrimonial_closing_entry_id"] is not None
        assert response.data["reopening_entry_id"] is not None
        assert response.data["lines"]
