import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.companies.models import Company
from apps.users.models import User


@pytest.mark.django_db
class TestCompanyApiContract:
    def test_list_companies_supports_all_and_selector_summary(self, api_client: APIClient):
        student = User.objects.create_user(
            username="student-companies",
            password="x",
            role=User.Role.STUDENT,
        )
        Company.objects.create(name="Empresa Uno", owner=student)
        Company.objects.create(name="Empresa Dos", owner=student)

        api_client.force_authenticate(student)
        response = api_client.get("/api/v1/companies/?all=true&summary=selector")

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["count"] == 2
        assert payload["next"] is None
        assert payload["previous"] is None
        assert sorted(item["name"] for item in payload["results"]) == [
            "Empresa Dos",
            "Empresa Uno",
        ]
