import uuid

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.example.models import Item


@pytest.mark.django_db
class TestPingEndpoint:
    def test_returns_pong(self, api_client: APIClient) -> None:
        response = api_client.get("/api/v1/ping")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "pong"}

    def test_includes_request_id_header(self, api_client: APIClient) -> None:
        response = api_client.get("/api/v1/ping")
        assert "X-Request-ID" in response


@pytest.mark.django_db
class TestItemCreateEndpoint:
    url = "/api/v1/items"

    def test_creates_item(self, api_client: APIClient) -> None:
        payload = {"name": "Widget", "description": "A widget."}
        response = api_client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Widget"
        assert data["description"] == "A widget."
        assert "id" in data
        assert "created_at" in data

    def test_persists_to_db(self, api_client: APIClient) -> None:
        api_client.post(self.url, {"name": "Stored"}, format="json")
        assert Item.objects.filter(name="Stored").exists()

    def test_name_required(self, api_client: APIClient) -> None:
        response = api_client.post(self.url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        body = response.json()
        assert body["error"]["code"] == "validation_error"

    def test_description_optional(self, api_client: APIClient) -> None:
        response = api_client.post(self.url, {"name": "No desc"}, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["description"] == ""


@pytest.mark.django_db
class TestItemDetailEndpoint:
    def _create_item(self) -> Item:
        return Item.objects.create(name="Existing", description="desc")

    def test_returns_item(self, api_client: APIClient) -> None:
        item = self._create_item()
        response = api_client.get(f"/api/v1/items/{item.pk}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert str(data["id"]) == str(item.pk)
        assert data["name"] == "Existing"

    def test_returns_404_for_unknown_id(self, api_client: APIClient) -> None:
        response = api_client.get(f"/api/v1/items/{uuid.uuid4()}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        body = response.json()
        assert body["error"]["code"] == "not_found"
