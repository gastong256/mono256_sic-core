"""
Services for the accounts app.

Business logic for creating, updating, and deleting hordak Accounts
at MPTT level=2 (spec depth-3 / student subcuentas).

Code format rules:
  - Input from user: full code like "1.04.01"
  - Regex: ^[1-9]\\.\\d{2}\\.\\d{2}$
  - Local code stored in hordak: the last ".XX" segment (e.g. ".01")
  - full_code is then computed by the PostgreSQL trigger

Uniqueness is checked via Account.full_code (globally unique field).
"""

import re

from django.db import transaction
from rest_framework.exceptions import ValidationError

from config.exceptions import ConflictError
from hordak.models import Account

from apps.companies.models import Company, CompanyAccount

# Regex for the full user-facing code: e.g. "1.04.01" or "2.06.03"
ACCOUNT_CODE_RE = re.compile(r"^[1-9]\.\d{2}\.\d{2}$")


def _validate_code_format(code: str) -> None:
    """Raise ValidationError if the code does not match X.XX.XX format."""
    if not ACCOUNT_CODE_RE.match(code):
        raise ValidationError(
            {"code": "Account code must match format X.XX.XX (e.g. 1.04.01)."}
        )


def _validate_code_unique(code: str, exclude_pk: int | None = None) -> None:
    """Raise ValidationError if the full_code already exists in hordak."""
    qs = Account.objects.filter(full_code=code)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        raise ValidationError({"code": f"Account code '{code}' already exists."})


def _extract_local_code(full_code: str) -> str:
    """
    Extract the local code portion from a full user-facing code.

    "1.04.01"  →  ".01"  (the dot + last two digits)
    """
    last_segment = full_code.rsplit(".", 1)[-1]
    return f".{last_segment}"


@transaction.atomic
def create_account(*, company: Company, name: str, code: str, parent_id: int) -> Account:
    """
    Create a new level-2 (MPTT) account for the given company.

    Validates:
    - parent exists and is MPTT level=1 (spec depth-2)
    - code format matches X.XX.XX
    - code is globally unique in hordak (via full_code)

    The local code stored in hordak is the last ".XX" segment of the full code.
    The type and currencies are inherited from the parent.
    """
    _validate_code_format(code)

    # Validate parent
    try:
        parent = Account.objects.get(pk=parent_id)
    except Account.DoesNotExist:
        raise ValidationError({"parent_id": "Parent account not found."})

    if parent.level != 1:
        raise ValidationError(
            {"parent_id": "Parent must be a level-2 account (colectiva)."}
        )

    _validate_code_unique(code)

    local_code = _extract_local_code(code)

    account = Account.objects.create(
        code=local_code,
        name=name,
        type=parent.type,
        currencies=parent.currencies,
        parent=parent,
    )

    CompanyAccount.objects.create(account=account, company=company)

    return account


@transaction.atomic
def update_account(
    *,
    account: Account,
    company: Company,
    name: str | None = None,
    code: str | None = None,
) -> Account:
    """
    Update the name and/or full code of a level-2 account belonging to the company.

    Raises ValidationError if the code is invalid or already taken.
    Raises PermissionDenied if the account does not belong to the company.
    """
    from rest_framework.exceptions import PermissionDenied

    if not CompanyAccount.objects.filter(account=account, company=company).exists():
        raise PermissionDenied("This account does not belong to your company.")

    if name is not None:
        account.name = name

    if code is not None:
        _validate_code_format(code)
        _validate_code_unique(code, exclude_pk=account.pk)
        account.code = _extract_local_code(code)

    account.save()
    account.refresh_from_db()
    return account


@transaction.atomic
def delete_account(*, account: Account, company: Company) -> None:
    """
    Delete a level-2 account belonging to the company.

    Raises PermissionDenied if the account does not belong to the company.
    Raises ConflictError (409) if the account has existing transaction legs.
    """
    from rest_framework.exceptions import PermissionDenied

    try:
        company_account = CompanyAccount.objects.get(account=account, company=company)
    except CompanyAccount.DoesNotExist:
        raise PermissionDenied("This account does not belong to your company.")

    if account.legs.exists():
        raise ConflictError(
            "Cannot delete account with existing transactions. "
            "Reverse the transactions first."
        )

    company_account.delete()
    account.delete()
