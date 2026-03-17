import pytest
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch

from apps.companies.models import Company
from apps.companies.models import CompanyAccount
from apps.companies import services as company_services
from apps.reports.services import journal_book, ledger, trial_balance
from apps.users.models import User
from hordak.models import Account


def _seed_opening_chart() -> dict[str, Account]:
    root_assets = Account.objects.create(code="1", name="ACTIVO", type="AS", currencies=["ARS"])
    parent_cash = Account.objects.create(
        code=".01", name="Caja", parent=root_assets, type="AS", currencies=["ARS"]
    )
    root_equity = Account.objects.create(
        code="3", name="PATRIMONIO NETO", type="EQ", currencies=["ARS"]
    )
    Account.objects.create(
        code=".01", name="Capital", parent=root_equity, type="EQ", currencies=["ARS"]
    )
    return {"cash": parent_cash}


@pytest.mark.django_db
class TestReportServiceAliases:
    def test_journal_book_returns_cached_payload_when_available(self):
        owner = User.objects.create_user(
            username="owner-jb-cache", password="x", role=User.Role.STUDENT
        )
        company = Company.objects.create(name="ACME JB Cache", owner=owner)
        cached = {"company_id": company.id, "entries": [], "cached": True}

        with patch(
            "apps.reports.services.journal_book.report_cache.get_cached_report",
            return_value=cached,
        ):
            report = journal_book.get_journal_book(company=company)

        assert report is cached

    def test_journal_book_returns_entries_only(self):
        owner = User.objects.create_user(username="owner-jb", password="x", role=User.Role.STUDENT)
        company = Company.objects.create(name="ACME JB", owner=owner)

        report = journal_book.get_journal_book(company=company)

        assert report["company_id"] == company.id
        assert report["entries"] == []
        assert "results" not in report
        assert report["grand_total_debit"] == report["totals"]["total_debit"]
        assert report["grand_total_credit"] == report["totals"]["total_credit"]

    def test_journal_book_marks_demo_reports_for_demo_cache(self):
        owner = User.objects.create_user(
            username="owner-jb-demo", password="x", role=User.Role.ADMIN
        )
        company = Company.objects.create(name="ACME JB Demo", owner=owner, is_demo=True)

        with patch("apps.reports.services.journal_book.report_cache.set_cached_report") as mock_set:
            journal_book.get_journal_book(company=company)

        assert mock_set.call_args.kwargs["is_demo"] is True

    def test_ledger_returns_cached_payload_when_available(self):
        owner = User.objects.create_user(
            username="owner-ledger-cache", password="x", role=User.Role.STUDENT
        )
        company = Company.objects.create(name="ACME Ledger Cache", owner=owner)
        cached = {"company_id": company.id, "accounts": [], "cached": True}

        with patch(
            "apps.reports.services.ledger.report_cache.get_cached_report",
            return_value=cached,
        ):
            report = ledger.get_ledger(company=company)

        assert report is cached

    def test_ledger_returns_accounts_only(self):
        owner = User.objects.create_user(
            username="owner-ledger", password="x", role=User.Role.STUDENT
        )
        company = Company.objects.create(name="ACME Ledger", owner=owner)

        report = ledger.get_ledger(company=company)

        assert report["company_id"] == company.id
        assert report["account_id"] is None
        assert report["accounts"] == []
        assert "cards" not in report

    def test_ledger_marks_demo_reports_for_demo_cache(self):
        owner = User.objects.create_user(
            username="owner-ledger-demo", password="x", role=User.Role.ADMIN
        )
        company = Company.objects.create(name="ACME Ledger Demo", owner=owner, is_demo=True)

        with patch("apps.reports.services.ledger.report_cache.set_cached_report") as mock_set:
            ledger.get_ledger(company=company)

        assert mock_set.call_args.kwargs["is_demo"] is True

    def test_trial_balance_returns_cached_payload_when_available(self):
        owner = User.objects.create_user(
            username="owner-trial-cache", password="x", role=User.Role.STUDENT
        )
        company = Company.objects.create(name="ACME TB Cache", owner=owner)
        cached = {"company_id": company.id, "groups": [], "cached": True}

        with patch(
            "apps.reports.services.trial_balance.report_cache.get_cached_report",
            return_value=cached,
        ):
            report = trial_balance.get_trial_balance(company=company)

        assert report is cached

    def test_trial_balance_returns_groups_only_and_grand_totals(self):
        owner = User.objects.create_user(
            username="owner-trial", password="x", role=User.Role.STUDENT
        )
        company = Company.objects.create(name="ACME TB", owner=owner)

        report = trial_balance.get_trial_balance(company=company)

        assert report["company_id"] == company.id
        assert report["groups"] == []
        assert "rows" not in report
        assert report["grand_total_debit"] == report["totals"]["total_debit"]
        assert report["grand_total_credit"] == report["totals"]["total_credit"]

    def test_trial_balance_marks_demo_reports_for_demo_cache(self):
        owner = User.objects.create_user(
            username="owner-trial-demo", password="x", role=User.Role.ADMIN
        )
        company = Company.objects.create(name="ACME TB Demo", owner=owner, is_demo=True)

        with patch(
            "apps.reports.services.trial_balance.report_cache.set_cached_report"
        ) as mock_set:
            trial_balance.get_trial_balance(company=company)

        assert mock_set.call_args.kwargs["is_demo"] is True

    def test_ledger_can_include_account_options(self, api_client: APIClient):
        owner = User.objects.create_user(
            username="owner-ledger-view", password="x", role=User.Role.STUDENT
        )
        parents = _seed_opening_chart()
        company = company_services.create_company_with_optional_opening(
            name="ACME Ledger View",
            owner=owner,
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
        account = (
            CompanyAccount.objects.filter(company=company)
            .exclude(account__parent__full_code="3.01")
            .get()
            .account
        )

        api_client.force_authenticate(owner)
        response = api_client.get(
            f"/api/v1/companies/{company.id}/reports/ledger/?account_id={account.id}&include=account_options"
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert sorted(payload["account_options"], key=lambda item: item["code"]) == [
            {"id": account.id, "code": account.full_code, "name": account.name},
            {
                "id": CompanyAccount.objects.get(
                    company=company,
                    account__parent__full_code="3.01",
                ).account_id,
                "code": "3.01.01",
                "name": "Capital",
            },
        ]

    def test_reports_are_blocked_until_company_has_opening_entry(self, api_client: APIClient):
        owner = User.objects.create_user(
            username="owner-ledger-no-opening", password="x", role=User.Role.STUDENT
        )
        company = Company.objects.create(name="ACME No Opening", owner=owner)

        api_client.force_authenticate(owner)
        response = api_client.get(f"/api/v1/companies/{company.id}/reports/trial-balance/")

        assert response.status_code == status.HTTP_409_CONFLICT
