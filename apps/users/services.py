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
