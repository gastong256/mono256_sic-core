import pytest
from unittest.mock import patch
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient


class TestLivenessEndpoint:
    def test_returns_ok(self, api_client: APIClient) -> None:
        response = api_client.get("/healthz")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ok"}


@pytest.mark.django_db
class TestReadinessEndpoint:
    def test_returns_ok_when_db_available(self, api_client: APIClient) -> None:
        response = api_client.get("/readyz")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ok", "db": True, "redis": False, "fallback": False}

    def test_hides_internal_error_details_when_db_unavailable(self, api_client: APIClient) -> None:
        with patch("django.db.connection.ensure_connection", side_effect=Exception("db is down")):
            response = api_client.get("/readyz")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.json() == {
            "status": "unavailable",
            "db": False,
            "redis": False,
            "fallback": False,
        }

    @override_settings(REDIS_URL="redis://example.test:6379/1")
    def test_returns_ok_when_db_and_redis_available(self, api_client: APIClient) -> None:
        with patch("config.urls.cache_roundtrip_ok", return_value=True) as mock_check:
            response = api_client.get("/readyz")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ok", "db": True, "redis": True, "fallback": False}
        mock_check.assert_called_once_with(key="__readyz__", value="ok", timeout=5)

    @override_settings(REDIS_URL="redis://example.test:6379/1")
    def test_returns_degraded_when_redis_check_fails(self, api_client: APIClient) -> None:
        with patch("config.urls.cache_roundtrip_ok", return_value=False):
            response = api_client.get("/readyz")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "degraded", "db": True, "redis": False, "fallback": True}
