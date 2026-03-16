import pytest
from unittest.mock import patch

from apps.users import services


@pytest.mark.django_db
class TestRegistrationSecurity:
    def test_generated_code_validates(self):
        info = services.get_current_registration_code_info()
        assert services.validate_registration_code(submitted_code=info["code"])

    def test_rate_limit_blocks_after_threshold(self):
        ip = "1.2.3.4"
        username = "student-x"
        attempts_before_block = min(services.REGISTER_IP_LIMIT, services.REGISTER_USERNAME_LIMIT)

        blocked = None
        for _ in range(attempts_before_block):
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

    def test_registration_code_still_works_when_cache_is_unavailable(self):
        with (
            patch("apps.common.cache.cache.get", side_effect=Exception("boom")),
            patch("apps.common.cache.cache.set", side_effect=Exception("boom")),
            patch("apps.common.cache.cache.delete", side_effect=Exception("boom")),
        ):
            info = services.get_current_registration_code_info()

        assert info["code"]
        assert services.validate_registration_code(submitted_code=info["code"])

    def test_rate_limit_degrades_without_cache_errors(self):
        with patch("apps.users.services.safe_cache_add", return_value=None):
            blocked = services.check_registration_limits(ip="7.8.9.10", username="student-z")

        assert blocked is None

    def test_failure_tracking_degrades_without_cache_errors(self):
        with patch("apps.users.services.safe_cache_add", return_value=None):
            cooldown = services.register_failure(ip="7.8.9.11", username="student-w")

        assert cooldown is None
