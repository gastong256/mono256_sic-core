from apps.users.models import User


def update_me(*, user: User, email: str | None = None, first_name: str | None = None, last_name: str | None = None) -> User:
    """Update editable profile fields of the authenticated user."""
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
    """Set a user role and keep Django's is_staff consistent with admin role."""
    valid_roles = {choice[0] for choice in User.Role.choices}
    if role not in valid_roles:
        raise ValueError(f"Invalid role: {role}")

    user.role = role
    user.is_staff = role == User.Role.ADMIN
    user.full_clean()
    user.save(update_fields=["role", "is_staff"])
    return user
