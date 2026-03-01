import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def authenticated_client(api_client: APIClient, django_user_model: type) -> APIClient:
    user = django_user_model.objects.create_user(username="testuser", password="pass")
    api_client.force_authenticate(user=user)
    return api_client
