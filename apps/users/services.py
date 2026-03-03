import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError

from apps.users.models import RegistrationCodeConfig, User

REGISTER_IP_LIMIT = 5
REGISTER_USERNAME_LIMIT = 3
REGISTER_WINDOW_SECONDS = 15 * 60
FAILURE_COUNTER_TTL = 60 * 60
COOLDOWN_STEPS = (
    (3, 60),
    (5, 5 * 60),
    (8, 15 * 60),
)


def update_me(*, user: User, email: str | None = None, first_name: str | None = None, last_name: str | None = None) -> User:
    if email is not None:
        user.email = email
    if first_name is not None:
        user.first_name = first_name
    if last_name is not None:
        user.last_name = last_name
    user.full_clean()
    user.save()
    return user


def set_user_role(*, user: User, role: str) -> User:
    valid_roles = {choice[0] for choice in User.Role.choices}
    if role not in valid_roles:
        raise ValueError(f"Invalid role: {role}")

    user.role = role
    user.is_staff = role == User.Role.ADMIN
    user.full_clean()
    user.save(update_fields=["role", "is_staff"])
    return user


def _current_epoch_seconds() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _normalize_registration_code(code: str) -> str:
    return "".join(ch for ch in code.upper() if ch.isalnum())


def _registration_config() -> RegistrationCodeConfig:
    config = RegistrationCodeConfig.objects.first()
    if config is not None:
        return config

    config = RegistrationCodeConfig(
        salt=secrets.token_urlsafe(32),
        window_minutes=60,
        allow_previous_window=True,
    )
    config.full_clean()
    config.save()
    return config


def _window_index(*, ts_epoch: int, window_minutes: int) -> int:
    window_seconds = max(1, window_minutes) * 60
    return ts_epoch // window_seconds


def _build_registration_code(*, salt: str, window_index: int) -> str:
    payload = f"{salt}:{window_index}".encode("utf-8")
    digest = hmac.new(
        key=settings.SECRET_KEY.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    ).digest()
    base = base64.b32encode(digest).decode("ascii").replace("=", "")
    compact = base[:10]
    return f"{compact[:5]}-{compact[5:]}"


def get_current_registration_code_info(*, at_epoch: int | None = None) -> dict:
    config = _registration_config()
    now_epoch = at_epoch if at_epoch is not None else _current_epoch_seconds()
    index = _window_index(ts_epoch=now_epoch, window_minutes=config.window_minutes)
    code = _build_registration_code(salt=config.salt, window_index=index)

    window_seconds = config.window_minutes * 60
    starts_at = index * window_seconds
    expires_at = starts_at + window_seconds

    return {
        "code": code,
        "window_minutes": config.window_minutes,
        "allow_previous_window": config.allow_previous_window,
        "valid_from": datetime.fromtimestamp(starts_at, tz=timezone.utc),
        "valid_until": datetime.fromtimestamp(expires_at, tz=timezone.utc),
    }


def rotate_registration_code() -> dict:
    config = _registration_config()
    config.salt = secrets.token_urlsafe(32)
    config.full_clean()
    config.save(update_fields=["salt", "updated_at"])
    return get_current_registration_code_info()


def validate_registration_code(*, submitted_code: str, at_epoch: int | None = None) -> bool:
    if not submitted_code:
        return False

    config = _registration_config()
    now_epoch = at_epoch if at_epoch is not None else _current_epoch_seconds()
    current_index = _window_index(ts_epoch=now_epoch, window_minutes=config.window_minutes)

    normalized = _normalize_registration_code(submitted_code)
    valid_codes = {
        _normalize_registration_code(_build_registration_code(salt=config.salt, window_index=current_index))
    }
    if config.allow_previous_window:
        valid_codes.add(
            _normalize_registration_code(
                _build_registration_code(salt=config.salt, window_index=current_index - 1)
            )
        )
    return normalized in valid_codes


def _consume_window_attempt(*, key: str, limit: int, window_seconds: int, now: datetime) -> int | None:
    now_ts = int(now.timestamp())
    attempts: list[int] = cache.get(key, [])
    cutoff = now_ts - window_seconds
    attempts = [ts for ts in attempts if ts > cutoff]
    if len(attempts) >= limit:
        retry_after = window_seconds - (now_ts - min(attempts))
        return max(retry_after, 1)
    attempts.append(now_ts)
    cache.set(key, attempts, timeout=window_seconds)
    return None


def _registration_keys(*, ip: str, username: str | None) -> dict:
    safe_username = (username or "").strip().lower()
    return {
        "ip_attempts": f"register:ip:{ip}",
        "username_attempts": f"register:user:{safe_username}" if safe_username else "",
        "fail_count": f"register:failcount:{ip}",
        "blocked_until": f"register:blocked_until:{ip}",
    }


def check_registration_limits(*, ip: str, username: str | None, now: datetime | None = None) -> int | None:
    now_dt = now or datetime.now(timezone.utc)
    keys = _registration_keys(ip=ip, username=username)

    blocked_until_epoch = cache.get(keys["blocked_until"])
    if blocked_until_epoch:
        retry_after = int(blocked_until_epoch - int(now_dt.timestamp()))
        if retry_after > 0:
            return retry_after

    retry_after = _consume_window_attempt(
        key=keys["ip_attempts"],
        limit=REGISTER_IP_LIMIT,
        window_seconds=REGISTER_WINDOW_SECONDS,
        now=now_dt,
    )
    if retry_after is not None:
        return retry_after

    if keys["username_attempts"]:
        retry_after = _consume_window_attempt(
            key=keys["username_attempts"],
            limit=REGISTER_USERNAME_LIMIT,
            window_seconds=REGISTER_WINDOW_SECONDS,
            now=now_dt,
        )
        if retry_after is not None:
            return retry_after

    return None


def register_failure(*, ip: str, username: str | None, now: datetime | None = None) -> int | None:
    now_dt = now or datetime.now(timezone.utc)
    keys = _registration_keys(ip=ip, username=username)
    fail_count = cache.get(keys["fail_count"], 0) + 1
    cache.set(keys["fail_count"], fail_count, timeout=FAILURE_COUNTER_TTL)

    cooldown = None
    for threshold, cooldown_seconds in COOLDOWN_STEPS:
        if fail_count >= threshold:
            cooldown = cooldown_seconds

    if cooldown:
        blocked_until = int((now_dt + timedelta(seconds=cooldown)).timestamp())
        cache.set(keys["blocked_until"], blocked_until, timeout=cooldown)
    return cooldown


def register_success(*, ip: str, username: str | None) -> None:
    keys = _registration_keys(ip=ip, username=username)
    cache.delete(keys["fail_count"])
    cache.delete(keys["blocked_until"])


def register_student_user(
    *,
    username: str,
    password: str,
    password_confirm: str,
    email: str = "",
    first_name: str = "",
    last_name: str = "",
    registration_code: str,
) -> User:
    if password != password_confirm:
        raise ValidationError({"password_confirm": "Passwords do not match."})

    candidate = User(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=User.Role.STUDENT,
    )

    try:
        validate_password(password=password, user=candidate)
    except DjangoValidationError as exc:
        raise ValidationError({"password": list(exc.messages)})

    if not validate_registration_code(submitted_code=registration_code):
        raise ValidationError({"registration_code": "Invalid registration code."})

    user = User.objects.create_user(
        username=username,
        password=password,
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=User.Role.STUDENT,
    )
    return user
