import pytest

from apps.users.models import User
from apps.users.services import set_user_role


@pytest.mark.django_db
class TestUserRoles:
    def test_set_teacher_role_clears_staff(self):
        user = User.objects.create_user(username="t1", password="x", is_staff=True)

        updated = set_user_role(user=user, role=User.Role.TEACHER)

        assert updated.role == User.Role.TEACHER
        assert updated.is_staff is False

    def test_set_admin_role_sets_staff(self):
        user = User.objects.create_user(username="a1", password="x", is_staff=False)

        updated = set_user_role(user=user, role=User.Role.ADMIN)

        assert updated.role == User.Role.ADMIN
        assert updated.is_staff is True
