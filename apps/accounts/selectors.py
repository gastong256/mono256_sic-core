"""
Selectors for the accounts app.

These functions build tree representations of hordak Accounts.
Hordak uses django-mptt (MPTTModel):
  account.level == 0  → rubros (spec depth-1)
  account.level == 1  → colectivas (spec depth-2)
  account.level == 2  → subcuentas per company (spec depth-3)

full_code is computed by a PostgreSQL trigger and represents the canonical account code.
"""

from hordak.models import Account

from apps.companies.models import Company


def _build_node(account: Account, children: list[dict] | None = None) -> dict:
    """Serialize a single Account node into a dict for API responses."""
    return {
        "id": account.pk,
        "code": account.full_code or account.code,
        "name": account.name,
        "type": account.type,
        "level": account.level,
        "is_leaf": account.is_leaf_node(),
        "children": children if children is not None else [],
    }


def get_global_chart() -> list[dict]:
    """
    Return the global chart of accounts (MPTT levels 0 and 1) as a nested list.

    Level-0 accounts are the rubros (ACTIVO, PASIVO, etc.).
    Level-1 accounts are the colectivas (Caja, Bancos, etc.).
    """
    # Fetch all level-0 and level-1 accounts in a single query, ordered for tree traversal.
    accounts = (
        Account.objects.filter(level__lte=1)
        .order_by("tree_id", "lft")
    )

    roots: dict[int, dict] = {}
    level1: dict[int, dict] = {}

    for acc in accounts:
        if acc.level == 0:
            node = _build_node(acc, children=[])
            roots[acc.pk] = node
        elif acc.level == 1:
            node = _build_node(acc, children=[])
            level1[acc.pk] = node
            if acc.parent_id in roots:
                roots[acc.parent_id]["children"].append(node)

    return list(roots.values())


def get_company_chart(*, company: Company) -> list[dict]:
    """
    Return the company-specific chart of accounts as a nested list.

    Includes:
    - All level-0 accounts (rubros) — global
    - All level-1 accounts (colectivas) — global
    - Level-2 accounts (subcuentas) that belong to this company
    """
    company_account_ids: set[int] = set(
        company.accounts.values_list("account_id", flat=True)
    )

    # Fetch all three levels in a single query.
    accounts = (
        Account.objects.filter(level__lte=2)
        .order_by("tree_id", "lft")
    )

    roots: dict[int, dict] = {}
    level1: dict[int, dict] = {}

    for acc in accounts:
        if acc.level == 0:
            node = _build_node(acc, children=[])
            roots[acc.pk] = node
        elif acc.level == 1:
            node = _build_node(acc, children=[])
            level1[acc.pk] = node
            if acc.parent_id in roots:
                roots[acc.parent_id]["children"].append(node)
        elif acc.level == 2 and acc.pk in company_account_ids:
            node = _build_node(acc, children=[])
            if acc.parent_id in level1:
                level1[acc.parent_id]["children"].append(node)

    return list(roots.values())
