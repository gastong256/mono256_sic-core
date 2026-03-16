import re

from django.db import transaction
from django.db.models import ProtectedError
from rest_framework.exceptions import ValidationError

from hordak.models import Account

from config.exceptions import ConflictError
from apps.companies.models import Company
from apps.companies.models import CompanyAccount
from apps.journal.models import JournalEntry

ACCOUNT_CODE_RE = re.compile(r"^[1-9]\.\d{2}\.\d{2}$")


def assert_company_writable(*, company: Company) -> None:
    if company.is_read_only:
        raise ConflictError("This is a read-only demo company.")


def create_company(
    *,
    name: str,
    description: str = "",
    tax_id: str = "",
    owner,
) -> Company:
    company = Company(name=name, description=description, tax_id=tax_id, owner=owner)
    company.full_clean()
    company.save()
    return company


def update_company(
    *,
    company: Company,
    name: str | None = None,
    description: str | None = None,
    tax_id: str | None = None,
) -> Company:
    assert_company_writable(company=company)
    if name is not None:
        company.name = name
    if description is not None:
        company.description = description
    if tax_id is not None:
        company.tax_id = tax_id
    company.full_clean()
    company.save()
    return company


def delete_company(*, company: Company) -> None:
    assert_company_writable(company=company)
    try:
        company.delete()
    except ProtectedError:
        raise ConflictError(
            "Cannot delete company with posted journal entries or protected records."
        )


def _extract_local_code(full_code: str) -> str:
    last_segment = full_code.rsplit(".", 1)[-1]
    return f".{last_segment}"


def _validate_opening_account_code(*, code: str, parent: Account) -> None:
    if not ACCOUNT_CODE_RE.match(code):
        raise ValidationError({"code": "Account code must match format X.XX.XX."})
    expected_prefix = f"{parent.full_code}."
    if not code.startswith(expected_prefix):
        raise ValidationError(
            {"code": f"Account code must start with '{expected_prefix}' for the selected parent."}
        )


def _resolve_opening_accounts(
    *,
    company: Company,
    actor,
    opening_lines: list[dict],
) -> dict[str, Account]:
    from apps.accounts.selectors import bump_company_chart_cache_version
    from apps.accounts.visibility import is_hidden_for_student
    from apps.users.models import User

    parent_codes = sorted({str(line["parent_code"]) for line in opening_lines})
    parents = {
        account.full_code: account for account in Account.objects.filter(full_code__in=parent_codes)
    }
    missing_parents = set(parent_codes) - set(parents.keys())
    if missing_parents:
        missing_parent = sorted(missing_parents)[0]
        raise ValidationError({"opening_entry": f"Parent account '{missing_parent}' not found."})

    requested_codes = sorted({str(line["code"]) for line in opening_lines})
    existing_accounts = {
        account.full_code: account
        for account in Account.objects.filter(full_code__in=requested_codes).select_related(
            "parent"
        )
    }
    accounts_by_code: dict[str, Account] = {}
    created_any = False

    specs_by_code: dict[str, tuple[str, str]] = {}
    for line in opening_lines:
        specs_by_code.setdefault(str(line["code"]), (str(line["name"]), str(line["parent_code"])))

    for code, (name, parent_code) in specs_by_code.items():
        parent = parents[parent_code]
        if parent.level != 1:
            raise ValidationError(
                {"opening_entry": f"Parent account '{parent_code}' must be a level-2 colectiva."}
            )
        if actor.role == User.Role.STUDENT and is_hidden_for_student(
            student=actor,
            account_id=parent.id,
        ):
            raise ValidationError(
                {"opening_entry": f"Parent account '{parent_code}' is hidden by your teacher."}
            )
        _validate_opening_account_code(code=code, parent=parent)

        account = existing_accounts.get(code)
        if account is None:
            account = Account.objects.create(
                code=_extract_local_code(code),
                name=name,
                type=parent.type,
                currencies=parent.currencies,
                parent=parent,
            )
            CompanyAccount.objects.create(account=account, company=company)
            created_any = True
        else:
            if account.parent_id != parent.id:
                raise ValidationError(
                    {"opening_entry": f"Account '{code}' already exists under a different parent."}
                )
            if account.level != 2 or not account.is_leaf_node():
                raise ValidationError(
                    {"opening_entry": f"Account '{code}' is not a movement account."}
                )
            if not CompanyAccount.objects.filter(account=account, company=company).exists():
                if CompanyAccount.objects.filter(account=account).exists():
                    raise ValidationError(
                        {
                            "opening_entry": (
                                f"Account '{code}' already exists and belongs to another company."
                            )
                        }
                    )
                CompanyAccount.objects.create(account=account, company=company)
                created_any = True
        accounts_by_code[code] = account

    if created_any:
        bump_company_chart_cache_version(company_id=company.id)

    return accounts_by_code


@transaction.atomic
def create_company_with_optional_opening(
    *,
    name: str,
    description: str = "",
    tax_id: str = "",
    owner,
    opening_entry: dict | None = None,
) -> Company:
    from apps.journal import services as journal_services

    company = create_company(
        name=name,
        description=description,
        tax_id=tax_id,
        owner=owner,
    )

    if not opening_entry:
        return company

    accounts_by_code = _resolve_opening_accounts(
        company=company,
        actor=owner,
        opening_lines=opening_entry["lines"],
    )
    journal_services.create_journal_entry(
        company=company,
        created_by=owner,
        date=opening_entry["date"],
        description=opening_entry["description"],
        source_type=opening_entry.get("source_type", JournalEntry.SourceType.MANUAL),
        source_ref=opening_entry.get("source_ref", ""),
        lines=[
            {
                "account_id": accounts_by_code[str(line["code"])].id,
                "type": line["type"],
                "amount": line["amount"],
            }
            for line in opening_entry["lines"]
        ],
    )
    return company
