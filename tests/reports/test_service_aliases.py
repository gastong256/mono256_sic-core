import pytest

from apps.companies.models import Company
from apps.reports.services import journal_book, ledger, trial_balance
from apps.users.models import User


@pytest.mark.django_db
class TestReportServiceAliases:
    def test_journal_book_includes_compatibility_aliases(self):
        owner = User.objects.create_user(username="owner-jb", password="x", role=User.Role.STUDENT)
        company = Company.objects.create(name="ACME JB", owner=owner)

        report = journal_book.get_journal_book(company=company)

        assert report["company_id"] == company.id
        assert report["results"] == report["entries"]
        assert report["grand_total_debit"] == report["totals"]["total_debit"]
        assert report["grand_total_credit"] == report["totals"]["total_credit"]

    def test_ledger_includes_cards_alias(self):
        owner = User.objects.create_user(
            username="owner-ledger", password="x", role=User.Role.STUDENT
        )
        company = Company.objects.create(name="ACME Ledger", owner=owner)

        report = ledger.get_ledger(company=company)

        assert report["company_id"] == company.id
        assert report["account_id"] is None
        assert report["cards"] == report["accounts"] == []

    def test_trial_balance_includes_rows_and_grand_totals(self):
        owner = User.objects.create_user(
            username="owner-trial", password="x", role=User.Role.STUDENT
        )
        company = Company.objects.create(name="ACME TB", owner=owner)

        report = trial_balance.get_trial_balance(company=company)

        assert report["company_id"] == company.id
        assert report["rows"] == report["groups"] == []
        assert report["grand_total_debit"] == report["totals"]["total_debit"]
        assert report["grand_total_credit"] == report["totals"]["total_credit"]
