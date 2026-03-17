import datetime

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.companies import services as company_services
from apps.users import services
from apps.users.models import User
from tests.support.opening import seed_opening_chart


@pytest.mark.django_db
class TestAuthApiContract:
    def test_me_requires_authentication(self, api_client: APIClient):
        response = api_client.get("/api/v1/auth/me/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_register_stays_public_without_authentication(self, api_client: APIClient):
        response = api_client.post("/api/v1/auth/register/", {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_companies_list_requires_authentication(self, api_client: APIClient):
        response = api_client.get("/api/v1/companies/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_include_companies_capabilities_and_registration_code(self, api_client: APIClient):
        teacher = User.objects.create_user(
            username="teacher-bootstrap",
            password="S3curePass123!",
            role=User.Role.TEACHER,
        )
        parents = seed_opening_chart()
        company_services.create_company_with_optional_opening(
            name="Empresa Demo",
            owner=teacher,
            opening_entry={
                "date": datetime.date(2026, 3, 16),
                "assets": [
                    {
                        "name": "Caja Principal",
                        "parent_code": parents["cash"].full_code,
                        "amount": "100.00",
                    }
                ],
            },
        )

        api_client.force_authenticate(teacher)
        response = api_client.get(
            "/api/v1/auth/me/?include=companies,capabilities,registration_code"
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["username"] == teacher.username
        assert payload["companies"][0]["name"] == "Empresa Demo"
        assert payload["companies"][0]["has_opening_entry"] is True
        assert payload["companies"][0]["accounting_ready"] is True
        assert payload["capabilities"]["can_manage_courses"] is True
        assert payload["registration_code"]["code"]

    def test_admin_users_support_all_and_selector_summary(self, api_client: APIClient):
        admin = User.objects.create_user(
            username="admin-users",
            password="S3curePass123!",
            role=User.Role.ADMIN,
        )
        User.objects.create_user(username="teacher-a", password="x", role=User.Role.TEACHER)
        User.objects.create_user(username="teacher-b", password="x", role=User.Role.TEACHER)

        api_client.force_authenticate(admin)
        response = api_client.get("/api/v1/admin/users/?role=teacher&all=true&summary=selector")

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["count"] == 2
        assert payload["next"] is None
        assert payload["previous"] is None
        assert payload["results"][0]["role"] == User.Role.TEACHER

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
