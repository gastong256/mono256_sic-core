from django.db.models import Q

from hordak.models import Account

from apps.accounts.models import TeacherAccountVisibility
from apps.accounts.visibility import hidden_account_ids_for_student
from apps.companies.models import Company
from apps.users.models import User


def _hidden_account_ids_for_user(*, user: User | None) -> set[int]:
    """Student visibility inherits teacher overrides via enrollment."""
    if user is None or user.role != User.Role.STUDENT:
        return set()
    return hidden_account_ids_for_student(student=user)


def _build_node(account: Account, children: list[dict] | None = None, is_visible: bool | None = None) -> dict:
    """Normalized tree node used by chart/visibility endpoints."""
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
    """Global Angrisani chart: rubros + colectivas, optionally filtered for student visibility."""
    hidden_account_ids = _hidden_account_ids_for_user(user=user)
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
    """Global levels + company subcuentas (movement accounts) in one nested tree."""
    hidden_account_ids = _hidden_account_ids_for_user(user=user)
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
    """Return effective show/hide state for levels 0/1 for one teacher scope."""
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
