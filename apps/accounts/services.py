import re

from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from config.exceptions import ConflictError
from hordak.models import Account

from apps.accounts.visibility import is_hidden_for_student
from apps.companies.models import Company, CompanyAccount
from apps.users.models import User

ACCOUNT_CODE_RE = re.compile(r"^[1-9]\.\d{2}\.\d{2}$")


def _validate_code_format(code: str) -> None:
    """Angrisani/SIC code format for subcuentas: X.XX.XX."""
    if not ACCOUNT_CODE_RE.match(code):
        raise ValidationError({"code": "Account code must match format X.XX.XX (e.g. 1.04.01)."})


def _validate_code_unique(code: str, exclude_pk: int | None = None) -> None:
    """Hordak full_code is global; duplicates are invalid across companies."""
    qs = Account.objects.filter(full_code=code)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        raise ValidationError({"code": f"Account code '{code}' already exists."})


def _extract_local_code(full_code: str) -> str:
    """Convert full code to Hordak local segment (e.g. 1.04.01 -> .01)."""
    last_segment = full_code.rsplit(".", 1)[-1]
    return f".{last_segment}"


def _validate_code_matches_parent(*, code: str, parent: Account) -> None:
    """Subcuenta must remain under its selected colectiva prefix."""
    if not parent.full_code:
        raise ValidationError({"parent_id": "Parent account has no full_code."})

    expected_prefix = f"{parent.full_code}."
    if not code.startswith(expected_prefix):
        raise ValidationError(
            {"code": f"Account code must start with '{expected_prefix}' for the selected parent."}
        )


@transaction.atomic
def create_account(
    *,
    company: Company,
    actor: User,
    name: str,
    code: str,
    parent_id: int,
) -> Account:
    """
    Create company subcuenta under a global colectiva (MPTT level=1).

    Angrisani model used here:
    - rubros/colectivas are global (levels 0/1)
    - subcuentas are company-specific (level=2 in Hordak MPTT)
    """
    _validate_code_format(code)
    try:
        parent = Account.objects.get(pk=parent_id)
    except Account.DoesNotExist:
        raise ValidationError({"parent_id": "Parent account not found."})

    if parent.level != 1:
        raise ValidationError({"parent_id": "Parent must be a level-2 account (colectiva)."})
    if actor.role == User.Role.STUDENT and is_hidden_for_student(
        student=actor, account_id=parent.pk
    ):
        raise ValidationError({"parent_id": "This account is hidden by your teacher."})

    _validate_code_matches_parent(code=code, parent=parent)
    _validate_code_unique(code)

    local_code = _extract_local_code(code)

    try:
        account = Account.objects.create(
            code=local_code,
            name=name,
            type=parent.type,
            currencies=parent.currencies,
            parent=parent,
        )
    except IntegrityError:
        raise ValidationError({"code": f"Account code '{code}' already exists."})

    CompanyAccount.objects.create(account=account, company=company)
    from apps.accounts.selectors import bump_company_chart_cache_version

    bump_company_chart_cache_version(company_id=company.id)

    return account


@transaction.atomic
def update_account(
    *,
    account: Account,
    company: Company,
    actor: User,
    name: str | None = None,
    code: str | None = None,
) -> Account:
    """Update only movement accounts (level=2 leaf) linked to the given company."""
    from rest_framework.exceptions import PermissionDenied

    if not CompanyAccount.objects.filter(account=account, company=company).exists():
        raise PermissionDenied("This account does not belong to your company.")

    if account.level != 2 or not account.is_leaf_node():
        raise ValidationError({"account": "Only level-3 movement accounts can be updated."})
    if (
        actor.role == User.Role.STUDENT
        and account.parent_id
        and is_hidden_for_student(
            student=actor,
            account_id=account.parent_id,
        )
    ):
        raise ValidationError({"account": "This account is hidden by your teacher."})

    if name is not None:
        account.name = name

    if code is not None:
        if not account.parent:
            raise ValidationError({"account": "Account parent is required."})
        _validate_code_format(code)
        _validate_code_matches_parent(code=code, parent=account.parent)
        _validate_code_unique(code, exclude_pk=account.pk)
        account.code = _extract_local_code(code)

    try:
        account.save()
    except IntegrityError:
        conflict_code = code or account.full_code or account.code
        raise ValidationError({"code": f"Account code '{conflict_code}' already exists."})
    account.refresh_from_db()

    from apps.accounts.selectors import bump_company_chart_cache_version

    bump_company_chart_cache_version(company_id=company.id)
    return account


@transaction.atomic
def delete_account(*, account: Account, company: Company) -> None:
    """Delete subcuenta only if it has no posted legs (double-entry integrity)."""
    from rest_framework.exceptions import PermissionDenied

    try:
        company_account = CompanyAccount.objects.get(account=account, company=company)
    except CompanyAccount.DoesNotExist:
        raise PermissionDenied("This account does not belong to your company.")

    if account.legs.exists():
        raise ConflictError(
            "Cannot delete account with existing transactions. " "Reverse the transactions first."
        )

    company_account.delete()
    account.delete()
    from apps.accounts.selectors import bump_company_chart_cache_version

    bump_company_chart_cache_version(company_id=company.id)
