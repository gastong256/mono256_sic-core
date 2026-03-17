from hordak.models import Account

from apps.companies.models import Company, CompanyAccount

GLOBAL_CLOSING_PARENT_SPECS = {
    "3.02": {"root_code": "3", "local_code": ".02", "name": "Resultado del Ejercicio"},
    "4.01": {"root_code": "4", "local_code": ".01", "name": "Costo de Mercaderías Vendidas"},
    "4.12": {"root_code": "4", "local_code": ".12", "name": "Faltante de Caja"},
    "4.13": {"root_code": "4", "local_code": ".13", "name": "Faltante de Mercaderías"},
    "5.06": {"root_code": "5", "local_code": ".06", "name": "Sobrante de Caja"},
    "5.07": {"root_code": "5", "local_code": ".07", "name": "Sobrante de Mercaderías"},
}

COMPANY_CLOSING_MOVEMENT_SPECS = (
    ("1.01", "Caja"),
    ("1.09", "Mercaderías"),
    ("3.02", "Resultado del Ejercicio"),
    ("4.01", "Costo de Mercaderías Vendidas"),
    ("4.12", "Faltante de Caja"),
    ("4.13", "Faltante de Mercaderías"),
    ("5.06", "Sobrante de Caja"),
    ("5.07", "Sobrante de Mercaderías"),
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
    raise ValueError(f"No more movement-account codes are available under {parent.full_code}.")


def ensure_closing_parent_accounts() -> dict[str, Account]:
    parents = {
        account.full_code: account
        for account in Account.objects.filter(full_code__in=GLOBAL_CLOSING_PARENT_SPECS.keys())
    }
    missing_codes = sorted(set(GLOBAL_CLOSING_PARENT_SPECS.keys()) - set(parents.keys()))

    for full_code in missing_codes:
        spec = GLOBAL_CLOSING_PARENT_SPECS[full_code]
        root = Account.objects.get(code=spec["root_code"], parent=None)
        parent = Account.objects.create(
            code=spec["local_code"],
            name=spec["name"],
            type=root.type,
            currencies=root.currencies,
            parent=root,
        )
        parents[parent.full_code] = parent

    return parents


def ensure_company_closing_accounts(*, company: Company) -> dict[tuple[str, str], Account]:
    ensure_closing_parent_accounts()
    parent_codes = sorted({parent_code for parent_code, _ in COMPANY_CLOSING_MOVEMENT_SPECS})
    parents = {
        account.full_code: account for account in Account.objects.filter(full_code__in=parent_codes)
    }

    existing_company_accounts = {
        (account.account.parent.full_code, account.account.name.strip().lower()): account.account
        for account in CompanyAccount.objects.select_related("account", "account__parent").filter(
            company=company,
            account__parent__full_code__in=parent_codes,
        )
    }

    resolved: dict[tuple[str, str], Account] = {}
    created_any = False
    for parent_code, name in COMPANY_CLOSING_MOVEMENT_SPECS:
        lookup_key = (parent_code, name.strip().lower())
        account = existing_company_accounts.get(lookup_key)
        if account is None:
            parent = parents[parent_code]
            full_code = _next_child_full_code(parent=parent)
            account = Account.objects.create(
                code=_extract_local_code(full_code),
                name=name,
                type=parent.type,
                currencies=parent.currencies,
                parent=parent,
            )
            CompanyAccount.objects.create(account=account, company=company)
            created_any = True
        resolved[lookup_key] = account

    if created_any:
        from apps.accounts.selectors import bump_company_chart_cache_version

        bump_company_chart_cache_version(company_id=company.id)

    return resolved
