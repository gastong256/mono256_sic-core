import pytest
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
