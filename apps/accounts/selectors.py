"""
Selectors for the accounts app.

These functions build tree representations of hordak Accounts.
Hordak uses django-mptt (MPTTModel):
  account.level == 0  → rubros (spec depth-1)
  account.level == 1  → colectivas (spec depth-2)
  account.level == 2  → subcuentas per company (spec depth-3)

full_code is computed by a PostgreSQL trigger and represents the canonical account code.
"""

from django.db.models import Q

from hordak.models import Account

from apps.accounts.models import TeacherAccountVisibility
from apps.accounts.visibility import hidden_account_ids_for_student
from apps.companies.models import Company
from apps.users.models import User


def _hidden_account_ids_for_user(*, user: User | None) -> set[int]:
    if user is None or user.role != User.Role.STUDENT:
        return set()
    return hidden_account_ids_for_student(student=user)


def _build_node(account: Account, children: list[dict] | None = None, is_visible: bool | None = None) -> dict:
    """Serialize a single Account node into a dict for API responses."""
    node = {
        "id": account.pk,
        "code": account.full_code or account.code,
        "name": account.name,
        "type": account.type,
        "level": account.level,
        "is_leaf": account.is_leaf_node(),
        "children": children if children is not None else [],
    }
    if is_visible is not None:
        node["is_visible"] = is_visible
    return node


def get_global_chart(*, user: User | None = None) -> list[dict]:
    """
    Return the global chart of accounts (MPTT levels 0 and 1) as a nested list.

    Level-0 accounts are the rubros (ACTIVO, PASIVO, etc.).
    Level-1 accounts are the colectivas (Caja, Bancos, etc.).
    """
    hidden_account_ids = _hidden_account_ids_for_user(user=user)

    # Fetch all level-0 and level-1 accounts in a single query, ordered for tree traversal.
    accounts = (
        Account.objects.filter(level__lte=1)
        .order_by("tree_id", "lft")
    )

    roots: dict[int, dict] = {}
    level1: dict[int, dict] = {}

    for acc in accounts:
        if acc.pk in hidden_account_ids:
            continue
        if acc.level == 0:
            node = _build_node(acc, children=[])
            roots[acc.pk] = node
        elif acc.level == 1:
            node = _build_node(acc, children=[])
            level1[acc.pk] = node
            if acc.parent_id in roots:
                roots[acc.parent_id]["children"].append(node)

    return list(roots.values())


def get_company_chart(*, company: Company, user: User | None = None) -> list[dict]:
    """
    Return the company-specific chart of accounts as a nested list.

    Includes:
    - All level-0 accounts (rubros) — global
    - All level-1 accounts (colectivas) — global
    - Level-2 accounts (subcuentas) that belong to this company
    """
    hidden_account_ids = _hidden_account_ids_for_user(user=user)

    # Fetch only global levels 0-1 plus level-2 accounts linked to this company.
    accounts = (
        Account.objects.filter(
            Q(level__lte=1)
            | Q(level=2, company_account__company=company)
        )
        .order_by("tree_id", "lft")
    )

    roots: dict[int, dict] = {}
    level1: dict[int, dict] = {}

    for acc in accounts:
        if acc.level <= 1 and acc.pk in hidden_account_ids:
            continue
        if acc.level == 0:
            node = _build_node(acc, children=[])
            roots[acc.pk] = node
        elif acc.level == 1:
            node = _build_node(acc, children=[])
            level1[acc.pk] = node
            if acc.parent_id in roots:
                roots[acc.parent_id]["children"].append(node)
        elif acc.level == 2:
            node = _build_node(acc, children=[])
            if acc.parent_id in level1:
                level1[acc.parent_id]["children"].append(node)

    return list(roots.values())


def get_teacher_visibility_chart(*, teacher: User) -> list[dict]:
    """Return level-0/1 account tree including effective visibility for one teacher."""
    overrides = {
        row["account_id"]: row["is_visible"]
        for row in TeacherAccountVisibility.objects.filter(teacher=teacher).values("account_id", "is_visible")
    }

    accounts = Account.objects.filter(level__lte=1).order_by("tree_id", "lft")
    roots: dict[int, dict] = {}
    level1: dict[int, dict] = {}

    for acc in accounts:
        visible = overrides.get(acc.pk, True)
        if acc.level == 0:
            node = _build_node(acc, children=[], is_visible=visible)
            roots[acc.pk] = node
        elif acc.level == 1:
            node = _build_node(acc, children=[], is_visible=visible)
            level1[acc.pk] = node
            if acc.parent_id in roots:
                roots[acc.parent_id]["children"].append(node)

    return list(roots.values())
