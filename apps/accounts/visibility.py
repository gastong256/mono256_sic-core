from django.conf import settings

from apps.common.cache import (
    safe_cache_add,
    safe_cache_delete,
    safe_cache_get,
    safe_cache_incr,
    safe_cache_set,
)
from apps.accounts.models import TeacherAccountVisibility
from apps.users.models import User

_VERSION_TTL_SECONDS = 30 * 24 * 60 * 60


def _cache_timeout() -> int:
    return int(getattr(settings, "ACCOUNT_VISIBILITY_CACHE_TIMEOUT", 300))


def _student_teacher_cache_key(student_id: int) -> str:
    return f"accounts:visibility:student:{student_id}:teacher"


def _teacher_visibility_version_key(teacher_id: int) -> str:
    return f"accounts:visibility:teacher:{teacher_id}:version"


def _teacher_hidden_ids_cache_key(teacher_id: int, version: int) -> str:
    return f"accounts:visibility:teacher:{teacher_id}:hidden:v{version}"


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


def invalidate_student_teacher_cache(*, student_id: int) -> None:
    safe_cache_delete(_student_teacher_cache_key(student_id))


def resolve_teacher_id_for_student(*, student: User) -> int | None:
    key = _student_teacher_cache_key(student.id)
    cached = safe_cache_get(key)
    if cached is not None:
        return int(cached) if cached else None

    from apps.courses.models import CourseEnrollment

    teacher_id = (
        CourseEnrollment.objects.filter(student=student)
        .values_list("course__teacher_id", flat=True)
        .first()
    )
    safe_cache_set(key, int(teacher_id) if teacher_id else 0, timeout=_cache_timeout())
    return int(teacher_id) if teacher_id else None


def resolve_teacher_for_student(*, student: User) -> User | None:
    teacher_id = resolve_teacher_id_for_student(student=student)
    if teacher_id is None:
        return None
    try:
        return User.objects.get(pk=teacher_id)
    except User.DoesNotExist:
        invalidate_student_teacher_cache(student_id=student.id)
        return None


def teacher_visibility_version(*, teacher_id: int) -> int:
    return _get_or_init_version(_teacher_visibility_version_key(teacher_id))


def bump_teacher_visibility_cache_version(*, teacher_id: int) -> None:
    _bump_version(_teacher_visibility_version_key(teacher_id))


def visibility_cache_token_for_student(*, student: User) -> str:
    teacher_id = resolve_teacher_id_for_student(student=student)
    if teacher_id is None:
        return "public"
    version = teacher_visibility_version(teacher_id=teacher_id)
    return f"teacher:{teacher_id}:v{version}"


def hidden_account_ids_for_student(*, student: User) -> set[int]:
    teacher_id = resolve_teacher_id_for_student(student=student)
    if teacher_id is None:
        return set()

    version = teacher_visibility_version(teacher_id=teacher_id)
    key = _teacher_hidden_ids_cache_key(teacher_id, version)
    cached = safe_cache_get(key)
    if cached is not None:
        return set(cached)

    hidden_ids = list(
        TeacherAccountVisibility.objects.filter(
            teacher_id=teacher_id,
            is_visible=False,
        ).values_list("account_id", flat=True)
    )
    safe_cache_set(key, hidden_ids, timeout=_cache_timeout())
    return set(hidden_ids)


def is_hidden_for_student(*, student: User, account_id: int) -> bool:
    return account_id in hidden_account_ids_for_student(student=student)
