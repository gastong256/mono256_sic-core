from django.conf import settings
from django.db.models import Q

from hordak.models import Account

from apps.common.cache import (
    safe_cache_add,
    safe_cache_get,
    safe_cache_incr,
    safe_cache_set,
)
from apps.accounts.models import TeacherAccountVisibility
from apps.accounts.visibility import (
    hidden_account_ids_for_student,
    teacher_visibility_version,
    visibility_cache_token_for_student,
)
from apps.companies.models import Company
from apps.users.models import User

_VERSION_TTL_SECONDS = 30 * 24 * 60 * 60


def _cache_timeout() -> int:
    return int(getattr(settings, "ACCOUNT_CHART_CACHE_TIMEOUT", 300))


def _demo_company_cache_timeout() -> int:
    return int(getattr(settings, "DEMO_COMPANY_CHART_CACHE_TIMEOUT", 900))


def _global_chart_version_key() -> str:
    return "accounts:chart:global:version"


def _company_chart_version_key(company_id: int) -> str:
    return f"accounts:chart:company:{company_id}:version"


def _get_or_init_version(key: str) -> int:
    current = safe_cache_get(key)
    if isinstance(current, int) and current > 0:
        return current
    safe_cache_set(key, 1, timeout=_VERSION_TTL_SECONDS)
    return 1


def _bump_version(key: str) -> int:
    if safe_cache_add(key, 2, timeout=_VERSION_TTL_SECONDS) is True:
        return 2
    value = safe_cache_incr(key)
    if value is None:
        current = safe_cache_get(key)
        if not isinstance(current, int):
            value = 2
        else:
            value = current + 1
        safe_cache_set(key, value, timeout=_VERSION_TTL_SECONDS)
    return int(value)


def bump_global_chart_cache_version() -> None:
    _bump_version(_global_chart_version_key())


def bump_company_chart_cache_version(*, company_id: int) -> None:
    _bump_version(_company_chart_version_key(company_id))


def _global_chart_cache_key(*, user: User | None) -> str:
    global_version = _get_or_init_version(_global_chart_version_key())
    if user is None or user.role != User.Role.STUDENT:
        return f"accounts:chart:global:public:v{global_version}"
    token = visibility_cache_token_for_student(student=user)
    return f"accounts:chart:global:student:{user.id}:{token}:v{global_version}"


def _company_chart_cache_key(*, company_id: int, user: User | None) -> str:
    company_version = _get_or_init_version(_company_chart_version_key(company_id))
    if user is None or user.role != User.Role.STUDENT:
        return f"accounts:chart:company:{company_id}:public:v{company_version}"
    token = visibility_cache_token_for_student(student=user)
    return f"accounts:chart:company:{company_id}:student:{user.id}:{token}:v{company_version}"


def _teacher_visibility_chart_cache_key(*, teacher_id: int) -> str:
    version = teacher_visibility_version(teacher_id=teacher_id)
    return f"accounts:chart:visibility:{teacher_id}:v{version}"


def _hidden_account_ids_for_user(*, user: User | None) -> set[int]:
    """Student visibility inherits teacher overrides via enrollment."""
    if user is None or user.role != User.Role.STUDENT:
        return set()
    return hidden_account_ids_for_student(student=user)


def _build_node(
    account: Account, children: list[dict] | None = None, is_visible: bool | None = None
) -> dict:
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
    cache_key = _global_chart_cache_key(user=user)
    cached = safe_cache_get(cache_key)
    if cached is not None:
        return cached

    hidden_account_ids = _hidden_account_ids_for_user(user=user)
    accounts = Account.objects.filter(level__lte=1).order_by("tree_id", "lft")

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

    tree = list(roots.values())
    safe_cache_set(cache_key, tree, timeout=_cache_timeout())
    return tree


def get_company_chart(*, company: Company, user: User | None = None) -> list[dict]:
    """Global levels + company subcuentas (movement accounts) in one nested tree."""
    cache_key = _company_chart_cache_key(company_id=company.id, user=user)
    cached = safe_cache_get(cache_key)
    if cached is not None:
        return cached

    hidden_account_ids = _hidden_account_ids_for_user(user=user)
    accounts = Account.objects.filter(
        Q(level__lte=1) | Q(level=2, company_account__company=company)
    ).order_by("tree_id", "lft")

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

    tree = list(roots.values())
    safe_cache_set(
        cache_key,
        tree,
        timeout=_demo_company_cache_timeout() if company.is_demo else _cache_timeout(),
    )
    return tree


def get_teacher_visibility_chart(*, teacher: User) -> list[dict]:
    """Return effective show/hide state for levels 0/1 for one teacher scope."""
    cache_key = _teacher_visibility_chart_cache_key(teacher_id=teacher.id)
    cached = safe_cache_get(cache_key)
    if cached is not None:
        return cached

    overrides = {
        row["account_id"]: row["is_visible"]
        for row in TeacherAccountVisibility.objects.filter(teacher=teacher).values(
            "account_id", "is_visible"
        )
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

    tree = list(roots.values())
    safe_cache_set(cache_key, tree, timeout=_cache_timeout())
    return tree
