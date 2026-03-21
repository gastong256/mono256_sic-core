from collections import defaultdict
from decimal import Decimal
from typing import Iterable

from django.db import transaction
from django.db.models import ProtectedError
from rest_framework.exceptions import ValidationError

from config.exceptions import ConflictError
from apps.companies.account_resolution import (
    MovementAccountResolutionSpec,
    account_resolution_key,
    resolve_company_movement_accounts,
)
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
from apps.journal.models import JournalEntry, JournalEntryLine
from apps.users.models import User


def assert_company_writable(*, company: Company) -> None:
    if company.is_read_only:
        raise ConflictError("This is a read-only demo company.")


def viewer_can_write_company(*, actor, company: Company) -> bool:
    if company.is_read_only:
        return False
    if actor is None:
        return True
    if actor.role == User.Role.ADMIN:
        return True
    if actor.role == User.Role.TEACHER:
        return True
    if actor.role == User.Role.STUDENT:
        return company.owner_id == actor.id
    return False


def assert_actor_can_write_company(*, actor, company: Company) -> None:
    assert_company_writable(company=company)
    if viewer_can_write_company(actor=actor, company=company):
        return
    raise ConflictError("This company is read-only for the current user.")


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
    actor,
    name: str | None = None,
    description: str | None = None,
    tax_id: str | None = None,
) -> Company:
    assert_actor_can_write_company(actor=actor, company=company)
    if name is not None:
        company.name = name
    if description is not None:
        company.description = description
    if tax_id is not None:
        company.tax_id = tax_id
    company.full_clean()
    company.save()
    return company


def delete_company(*, company: Company, actor) -> None:
    assert_actor_can_write_company(actor=actor, company=company)
    try:
        company.delete()
    except ProtectedError:
        raise ConflictError(
            "Cannot delete company with posted journal entries or protected records."
        )


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
    return account_resolution_key(parent_code=parent_code, name=name)


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
    accounts_by_spec = resolve_company_movement_accounts(
        company=company,
        actor=actor,
        specs=[
            MovementAccountResolutionSpec(parent_code=spec.parent_code, name=spec.name)
            for spec in account_specs
        ],
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
    assert_actor_can_write_company(actor=actor, company=company)
    assert_can_manage_company_opening(actor=actor, company=company)
    return _create_opening_entry(company=company, actor=actor, opening_entry=opening_entry)


def set_demo_publication(*, company: Company, is_published: bool) -> Company:
    if not company.is_demo:
        raise ValidationError({"company": "Only demo companies can change publication status."})
    if company.is_published == is_published:
        return company
    company.is_published = is_published
    company.full_clean()
    company.save(update_fields=["is_published", "updated_at"])
    return company
