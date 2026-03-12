import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.users import services
from apps.users.models import User


@pytest.mark.django_db
class TestAuthApiContract:
    def test_token_refresh_returns_refresh_field(self, api_client: APIClient):
        User.objects.create_user(username="refresh-user", password="S3curePass123!")

        token_response = api_client.post(
            "/api/v1/auth/token/",
            {"username": "refresh-user", "password": "S3curePass123!"},
            format="json",
        )
        assert token_response.status_code == status.HTTP_200_OK
        refresh = token_response.json()["refresh"]

        refresh_response = api_client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": refresh},
            format="json",
        )
        assert refresh_response.status_code == status.HTTP_200_OK
        payload = refresh_response.json()
        assert payload.get("access")
        assert payload.get("refresh")

    def test_register_throttle_includes_retry_after(self, api_client: APIClient):
        info = services.get_current_registration_code_info()
        ip = "10.20.30.40"
        attempts_before_block = services.REGISTER_IP_LIMIT

        for idx in range(attempts_before_block):
            api_client.post(
                "/api/v1/auth/register/",
                {
                    "username": f"rate-limited-user-{idx}",
                    "password": "S3curePass123!",
                    "password_confirm": "S3curePass123!",
                    "registration_code": info["code"],
                },
                format="json",
                REMOTE_ADDR=ip,
            )

        blocked = api_client.post(
            "/api/v1/auth/register/",
            {
                "username": "rate-limited-user-blocked",
                "password": "S3curePass123!",
                "password_confirm": "S3curePass123!",
                "registration_code": info["code"],
            },
            format="json",
            REMOTE_ADDR=ip,
        )
        assert blocked.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        body = blocked.json()
        assert isinstance(body.get("retry_after"), int)
        assert body["retry_after"] > 0
        assert body["error"]["code"] == "throttled"
        assert body["error"]["detail"]["retry_after"] == body["retry_after"]
