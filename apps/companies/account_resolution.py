import re
from dataclasses import dataclass

from rest_framework.exceptions import ValidationError

from hordak.models import Account

from config.exceptions import ConflictError
from apps.companies.models import Company, CompanyAccount

ACCOUNT_CODE_RE = re.compile(r"^[1-9]\.\d{2}\.\d{2}$")


@dataclass(frozen=True)
class MovementAccountResolutionSpec:
    parent_code: str
    name: str


def account_resolution_key(*, parent_code: str, name: str) -> str:
    return f"{parent_code}|{name.strip().lower()}"


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


def resolve_company_movement_accounts(
    *,
    company: Company,
    actor,
    specs: list[MovementAccountResolutionSpec],
) -> dict[str, Account]:
    from apps.accounts.selectors import bump_company_chart_cache_version
    from apps.accounts.visibility import is_hidden_for_student
    from apps.users.models import User

    parent_codes = sorted({spec.parent_code for spec in specs})
    parents = {
        account.full_code: account for account in Account.objects.filter(full_code__in=parent_codes)
    }
    missing_parents = set(parent_codes) - set(parents.keys())
    if missing_parents:
        missing_parent = sorted(missing_parents)[0]
        raise ValidationError({"accounts": f"Parent account '{missing_parent}' not found."})

    existing_company_accounts = {
        (row.account.parent.full_code, row.account.name.strip().lower()): row.account
        for row in CompanyAccount.objects.select_related("account", "account__parent").filter(
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

    for spec in specs:
        parent = parents[spec.parent_code]
        if parent.level != 1:
            raise ValidationError(
                {"accounts": f"Parent account '{spec.parent_code}' must be a level-2 colectiva."}
            )

        if actor.role == User.Role.STUDENT and is_hidden_for_student(
            student=actor,
            account_id=parent.id,
        ):
            raise ValidationError(
                {"accounts": f"Parent account '{spec.parent_code}' is hidden by your teacher."}
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
                    account = None
                else:
                    CompanyAccount.objects.create(account=account, company=company)
                    created_any = True
                    existing_company_accounts[lookup_key] = account

        if account is None:
            full_code = _next_child_full_code(parent=parent)
            if not ACCOUNT_CODE_RE.match(full_code):
                raise ValidationError({"accounts": f"Generated code '{full_code}' is invalid."})
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
                {"accounts": f"Account '{account.full_code}' is not a movement account."}
            )

        accounts_by_spec_key[
            account_resolution_key(parent_code=spec.parent_code, name=spec.name)
        ] = account

    if created_any:
        bump_company_chart_cache_version(company_id=company.id)

    return accounts_by_spec_key
