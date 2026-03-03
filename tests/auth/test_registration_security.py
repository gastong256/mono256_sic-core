import pytest

from apps.users import services


@pytest.mark.django_db
class TestRegistrationSecurity:
    def test_generated_code_validates(self):
        info = services.get_current_registration_code_info()
        assert services.validate_registration_code(submitted_code=info["code"])

    def test_rate_limit_blocks_after_threshold(self):
        ip = "1.2.3.4"
        username = "student-x"

        blocked = None
        for _ in range(services.REGISTER_IP_LIMIT):
            blocked = services.check_registration_limits(ip=ip, username=username)
            assert blocked is None

        blocked = services.check_registration_limits(ip=ip, username=username)
        assert blocked is not None

    def test_cooldown_applies_after_repeated_failures(self):
        ip = "5.6.7.8"
        username = "student-y"

        cooldown = None
        for _ in range(3):
            cooldown = services.register_failure(ip=ip, username=username)

        assert cooldown is not None
        retry_after = services.check_registration_limits(ip=ip, username=username)
        assert retry_after is not None
