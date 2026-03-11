import pytest
from unittest.mock import patch
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
        assert response.json() == {"status": "ok"}

    def test_hides_internal_error_details_when_db_unavailable(self, api_client: APIClient) -> None:
        with patch("django.db.connection.ensure_connection", side_effect=Exception("db is down")):
            response = api_client.get("/readyz")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.json() == {"status": "unavailable"}
