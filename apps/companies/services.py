import re
from collections import defaultdict
from decimal import Decimal
from typing import Iterable

from django.db import transaction
from django.db.models import ProtectedError
from rest_framework.exceptions import ValidationError

from hordak.models import Account

from config.exceptions import ConflictError
from apps.companies.opening import (
    OPENING_CAPITAL_PARENT_CODE,
    OpeningAccountSpec,
    OpeningEntryPayload,
    assert_can_manage_company_opening,
    build_opening_entry_payload,
    company_has_opening_entry,
    opening_description_for_kind,
)
from apps.companies.models import Company
from apps.companies.models import CompanyAccount
from apps.journal.models import JournalEntry, JournalEntryLine

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


def _next_child_full_code(*, parent: Account) -> str:
    suffixes: set[int] = set()
    for code in Account.objects.filter(parent=parent).values_list("code", flat=True):
        try:
            suffixes.add(int(str(code).replace(".", "")))
        except ValueError:
            continue

    for candidate in range(1, 100):
        if candidate not in suffixes:
            return f"{parent.full_code}.{candidate:02d}"
    raise ConflictError(f"No more movement-account codes are available under {parent.full_code}.")


def _resolve_opening_accounts(
    *,
    company: Company,
    actor,
    account_specs: list[OpeningAccountSpec],
) -> dict[str, Account]:
    from apps.accounts.selectors import bump_company_chart_cache_version
    from apps.accounts.visibility import is_hidden_for_student
    from apps.users.models import User

    parent_codes = sorted({spec.parent_code for spec in account_specs})
    parents = {
        account.full_code: account for account in Account.objects.filter(full_code__in=parent_codes)
    }
    missing_parents = set(parent_codes) - set(parents.keys())
    if missing_parents:
        missing_parent = sorted(missing_parents)[0]
        raise ValidationError({"opening_entry": f"Parent account '{missing_parent}' not found."})

    existing_company_accounts = {
        (account.account.parent.full_code, account.account.name.strip().lower()): account.account
        for account in CompanyAccount.objects.select_related("account", "account__parent").filter(
            company=company,
            account__parent__full_code__in=parent_codes,
        )
    }
    existing_parent_name_accounts = {
        (account.parent.full_code, account.name.strip().lower()): account
        for account in Account.objects.select_related("parent").filter(
            parent__full_code__in=parent_codes
        )
    }
    accounts_by_spec_key: dict[str, Account] = {}
    created_any = False

    for spec in account_specs:
        parent = parents[spec.parent_code]
        if parent.level != 1:
            raise ValidationError(
                {
                    "opening_entry": f"Parent account '{spec.parent_code}' must be a level-2 colectiva."
                }
            )
        if actor.role == User.Role.STUDENT and is_hidden_for_student(
            student=actor,
            account_id=parent.id,
        ):
            raise ValidationError(
                {"opening_entry": f"Parent account '{spec.parent_code}' is hidden by your teacher."}
            )
        lookup_key = (spec.parent_code, spec.name.strip().lower())
        account = existing_company_accounts.get(lookup_key)
        if account is None:
            account = existing_parent_name_accounts.get(lookup_key)
            if (
                account is not None
                and not CompanyAccount.objects.filter(account=account, company=company).exists()
            ):
                if CompanyAccount.objects.filter(account=account).exists():
                    raise ValidationError(
                        {
                            "opening_entry": (
                                f"Account '{account.full_code}' already exists and belongs to another company."
                            )
                        }
                    )
                CompanyAccount.objects.create(account=account, company=company)
                created_any = True
                existing_company_accounts[lookup_key] = account

        if account is None:
            full_code = _next_child_full_code(parent=parent)
            if not ACCOUNT_CODE_RE.match(full_code):
                raise ValidationError(
                    {"opening_entry": f"Generated code '{full_code}' is invalid."}
                )
            account = Account.objects.create(
                code=_extract_local_code(full_code),
                name=spec.name,
                type=parent.type,
                currencies=parent.currencies,
                parent=parent,
            )
            CompanyAccount.objects.create(account=account, company=company)
            created_any = True
            existing_company_accounts[lookup_key] = account
        elif account.level != 2 or not account.is_leaf_node():
            raise ValidationError(
                {"opening_entry": f"Account '{account.full_code}' is not a movement account."}
            )

        accounts_by_spec_key[f"{spec.parent_code}|{spec.name.strip().lower()}"] = account

    if created_any:
        bump_company_chart_cache_version(company_id=company.id)

    return accounts_by_spec_key


def _build_opening_specs(
    *, payload_items: Iterable[OpeningAccountSpec]
) -> list[OpeningAccountSpec]:
    grouped: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    for item in payload_items:
        grouped[(item.parent_code, item.name.strip())] += item.amount
    return [
        OpeningAccountSpec(parent_code=parent_code, name=name, amount=amount)
        for (parent_code, name), amount in grouped.items()
    ]


def _opening_spec_key(*, parent_code: str, name: str) -> str:
    return f"{parent_code}|{name.strip().lower()}"


def _create_opening_entry(
    *,
    company: Company,
    actor,
    opening_entry: dict,
) -> JournalEntry:
    if company_has_opening_entry(company=company):
        raise ConflictError("This company already has an opening entry.")
    if company.journal_entries.exists():
        raise ConflictError("Opening entry must be the first accounting entry of the company.")

    opening_payload = build_opening_entry_payload(data=opening_entry)
    return _create_opening_entry_from_payload(
        company=company,
        actor=actor,
        opening_payload=opening_payload,
    )


def _create_opening_entry_from_payload(
    *,
    company: Company,
    actor,
    opening_payload: OpeningEntryPayload,
) -> JournalEntry:
    from apps.journal import services as journal_services

    asset_specs = _build_opening_specs(payload_items=opening_payload.assets)
    liability_specs = _build_opening_specs(payload_items=opening_payload.liabilities)

    assets_total = sum((spec.amount for spec in asset_specs), start=Decimal("0"))
    liabilities_total = sum((spec.amount for spec in liability_specs), start=Decimal("0"))
    capital_amount = assets_total - liabilities_total
    if capital_amount <= 0:
        raise ValidationError(
            {
                "opening_entry": (
                    "Capital must be greater than zero. Total assets must exceed total liabilities."
                )
            }
        )

    account_specs = (
        asset_specs
        + liability_specs
        + [
            OpeningAccountSpec(
                parent_code=OPENING_CAPITAL_PARENT_CODE,
                name="Capital",
                amount=capital_amount,
            )
        ]
    )
    accounts_by_spec = _resolve_opening_accounts(
        company=company,
        actor=actor,
        account_specs=account_specs,
    )
    description = opening_description_for_kind(inventory_kind=opening_payload.inventory_kind)

    lines = [
        {
            "account_id": accounts_by_spec[
                _opening_spec_key(parent_code=spec.parent_code, name=spec.name)
            ].id,
            "type": JournalEntryLine.LineType.DEBIT,
            "amount": spec.amount,
        }
        for spec in asset_specs
    ]
    lines += [
        {
            "account_id": accounts_by_spec[
                _opening_spec_key(parent_code=spec.parent_code, name=spec.name)
            ].id,
            "type": JournalEntryLine.LineType.CREDIT,
            "amount": spec.amount,
        }
        for spec in liability_specs
    ]
    lines.append(
        {
            "account_id": accounts_by_spec[
                _opening_spec_key(parent_code=OPENING_CAPITAL_PARENT_CODE, name="Capital")
            ].id,
            "type": JournalEntryLine.LineType.CREDIT,
            "amount": capital_amount,
        }
    )

    return journal_services.create_journal_entry(
        company=company,
        created_by=actor,
        date=opening_payload.date,
        description=description,
        source_type=JournalEntry.SourceType.OPENING,
        source_ref=opening_payload.source_ref,
        lines=lines,
    )


@transaction.atomic
def create_company_with_optional_opening(
    *,
    name: str,
    description: str = "",
    tax_id: str = "",
    owner,
    opening_entry: dict | None = None,
) -> Company:
    company = create_company(
        name=name,
        description=description,
        tax_id=tax_id,
        owner=owner,
    )

    if not opening_entry:
        return company

    _create_opening_entry(company=company, actor=owner, opening_entry=opening_entry)
    return company


@transaction.atomic
def create_company_opening_entry(
    *,
    company: Company,
    actor,
    opening_entry: dict,
) -> JournalEntry:
    assert_company_writable(company=company)
    assert_can_manage_company_opening(actor=actor, company=company)
    return _create_opening_entry(company=company, actor=actor, opening_entry=opening_entry)
