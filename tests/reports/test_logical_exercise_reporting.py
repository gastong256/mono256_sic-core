import datetime
from unittest.mock import patch

import pytest
from django.core.management import call_command

from apps.accounts import services as account_services
from apps.closing import services as closing_services
from apps.companies import services as company_services
from apps.companies.models import CompanyAccount
from apps.journal import services as journal_services
from apps.journal.models import JournalEntry
from apps.reports.services import journal_book, ledger, trial_balance
from apps.users.models import User
from hordak.models import Account


def _parent(full_code: str) -> Account:
    return Account.objects.get(full_code=full_code)


def _open_company(*, owner: User):
    return company_services.create_company_with_optional_opening(
        name="Empresa Reportes Ejercicio",
        owner=owner,
        opening_entry={
            "date": datetime.date(2026, 1, 1),
            "assets": [
                {"name": "Caja Principal", "parent_code": "1.01", "amount": "1000.00"},
            ],
        },
    )


@pytest.mark.django_db
class TestLogicalExerciseReporting:
    def setup_method(self):
        call_command("load_chart_of_accounts")

    def test_reports_return_active_exercise_and_previous_references(self):
        owner = User.objects.create_user(
            username="owner-logical-reporting",
            password="x",
            role=User.Role.STUDENT,
        )
        company = _open_company(owner=owner)
        sales_account = account_services.create_account(
            company=company,
            actor=owner,
            name="Ventas 2026",
            code="5.01.01",
            parent_id=_parent("5.01").id,
        )
        cash_account = CompanyAccount.objects.get(
            company=company,
            account__parent__full_code="1.01",
            account__name="Caja Principal",
        ).account

        journal_services.create_journal_entry(
            company=company,
            created_by=owner,
            date=datetime.date(2026, 6, 1),
            description="Venta 2026",
            source_type=JournalEntry.SourceType.MANUAL,
            lines=[
                {"account_id": cash_account.id, "type": "DEBIT", "amount": "100.00"},
                {"account_id": sales_account.id, "type": "CREDIT", "amount": "100.00"},
            ],
        )

        closing_services.execute_simplified_closing(
            company=company,
            actor=owner,
            data={
                "closing_date": datetime.date(2026, 12, 31),
                "reopening_date": datetime.date(2027, 1, 1),
            },
        )

        journal_services.create_journal_entry(
            company=company,
            created_by=owner,
            date=datetime.date(2027, 2, 1),
            description="Venta 2027",
            source_type=JournalEntry.SourceType.MANUAL,
            lines=[
                {"account_id": cash_account.id, "type": "DEBIT", "amount": "50.00"},
                {"account_id": sales_account.id, "type": "CREDIT", "amount": "50.00"},
            ],
        )

        jb_report = journal_book.get_journal_book(
            company=company,
            date_from=datetime.date(2026, 3, 10),
            date_to=datetime.date(2027, 3, 17),
        )
        assert jb_report["requested_range"] == {
            "date_from": "2026-03-10",
            "date_to": "2027-03-17",
        }
        assert jb_report["exercise_range"] == {
            "date_from": "2027-01-01",
            "date_to": None,
            "status": "open",
        }
        assert jb_report["visible_range"] == {
            "date_from": "2027-01-01",
            "date_to": "2027-03-17",
        }
        assert jb_report["active_exercise"]["start_date"] == "2027-01-01"
        assert jb_report["previous_exercises"][0]["start_date"] == "2026-01-01"
        assert all(entry["date"] >= "2027-01-01" for entry in jb_report["entries"])

        ledger_report = ledger.get_ledger(
            company=company,
            date_from=datetime.date(2026, 3, 10),
            date_to=datetime.date(2027, 3, 17),
            account_id=cash_account.id,
        )
        assert ledger_report["requested_range"] == {
            "date_from": "2026-03-10",
            "date_to": "2027-03-17",
        }
        assert ledger_report["exercise_range"] == {
            "date_from": "2027-01-01",
            "date_to": None,
            "status": "open",
        }
        assert ledger_report["visible_range"] == {
            "date_from": "2027-01-01",
            "date_to": "2027-03-17",
        }
        assert ledger_report["active_exercise"]["start_date"] == "2027-01-01"
        assert ledger_report["accounts"][0]["opening_balance"] == "0.00"
        assert ledger_report["accounts"][0]["movements"][0]["date"] == "2027-01-01"

        trial_report = trial_balance.get_trial_balance(
            company=company,
            date_from=datetime.date(2026, 3, 10),
            date_to=datetime.date(2027, 3, 17),
        )
        assert trial_report["requested_range"] == {
            "date_from": "2026-03-10",
            "date_to": "2027-03-17",
        }
        assert trial_report["exercise_range"] == {
            "date_from": "2027-01-01",
            "date_to": None,
            "status": "open",
        }
        assert trial_report["visible_range"] == {
            "date_from": "2027-01-01",
            "date_to": "2027-03-17",
        }
        assert trial_report["active_exercise"]["start_date"] == "2027-01-01"
        assert trial_report["date_from"] == "2027-01-01"

    def test_report_cache_uses_resolved_logical_exercise_window(self):
        owner = User.objects.create_user(
            username="owner-logical-cache-window",
            password="x",
            role=User.Role.STUDENT,
        )
        company = _open_company(owner=owner)
        sales_account = account_services.create_account(
            company=company,
            actor=owner,
            name="Ventas Cache",
            code="5.01.01",
            parent_id=_parent("5.01").id,
        )
        cash_account = CompanyAccount.objects.get(
            company=company,
            account__parent__full_code="1.01",
            account__name="Caja Principal",
        ).account

        journal_services.create_journal_entry(
            company=company,
            created_by=owner,
            date=datetime.date(2026, 6, 1),
            description="Venta 2026",
            source_type=JournalEntry.SourceType.MANUAL,
            lines=[
                {"account_id": cash_account.id, "type": "DEBIT", "amount": "100.00"},
                {"account_id": sales_account.id, "type": "CREDIT", "amount": "100.00"},
            ],
        )
        closing_services.execute_simplified_closing(
            company=company,
            actor=owner,
            data={
                "closing_date": datetime.date(2026, 12, 31),
                "reopening_date": datetime.date(2027, 1, 1),
            },
        )

        with patch("apps.reports.services.journal_book.report_cache.set_cached_report") as jb_set:
            journal_book.get_journal_book(
                company=company,
                date_from=datetime.date(2026, 3, 10),
                date_to=datetime.date(2027, 3, 17),
            )

        assert jb_set.call_args.kwargs["date_from"] == datetime.date(2027, 1, 1)
        assert jb_set.call_args.kwargs["date_to"] == datetime.date(2027, 3, 17)
        assert jb_set.call_args.kwargs["extra_parts"]["exercise_id"].startswith("reopening:")

        with patch("apps.reports.services.ledger.report_cache.set_cached_report") as ledger_set:
            ledger.get_ledger(
                company=company,
                date_from=datetime.date(2026, 3, 10),
                date_to=datetime.date(2027, 3, 17),
                account_id=cash_account.id,
            )

        assert ledger_set.call_args.kwargs["date_from"] == datetime.date(2027, 1, 1)
        assert ledger_set.call_args.kwargs["date_to"] == datetime.date(2027, 3, 17)
        assert ledger_set.call_args.kwargs["extra_parts"]["account_id"] == cash_account.id

        with patch(
            "apps.reports.services.trial_balance.report_cache.set_cached_report"
        ) as trial_set:
            trial_balance.get_trial_balance(
                company=company,
                date_from=datetime.date(2026, 3, 10),
                date_to=datetime.date(2027, 3, 17),
            )

        assert trial_set.call_args.kwargs["date_from"] == datetime.date(2027, 1, 1)
        assert trial_set.call_args.kwargs["date_to"] == datetime.date(2027, 3, 17)
