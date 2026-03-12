import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.companies.models import Company
from apps.courses.models import Course, CourseEnrollment
from apps.users.models import User


@pytest.mark.django_db
class TestTeacherCourseAggregatedEndpoints:
    def test_companies_summary_returns_grouped_students(self, api_client: APIClient):
        teacher = User.objects.create_user(
            username="teacher-api", password="x", role=User.Role.TEACHER
        )
        student = User.objects.create_user(
            username="student-api", password="x", role=User.Role.STUDENT
        )
        course = Course.objects.create(name="Curso API", teacher=teacher)
        CourseEnrollment.objects.create(course=course, student=student)
        Company.objects.create(name="Empresa Uno", owner=student)

        api_client.force_authenticate(teacher)
        response = api_client.get(f"/api/v1/teacher/courses/{course.id}/companies/summary/")

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["course_id"] == course.id
        assert len(payload["students"]) == 1
        assert payload["students"][0]["student_id"] == student.id
        assert len(payload["students"][0]["companies"]) == 1

    def test_journal_entries_all_returns_single_payload(self, api_client: APIClient):
        teacher = User.objects.create_user(
            username="teacher-api2", password="x", role=User.Role.TEACHER
        )
        student = User.objects.create_user(
            username="student-api2", password="x", role=User.Role.STUDENT
        )
        course = Course.objects.create(name="Curso API 2", teacher=teacher)
        CourseEnrollment.objects.create(course=course, student=student)

        api_client.force_authenticate(teacher)
        response = api_client.get(f"/api/v1/teacher/courses/{course.id}/journal-entries/all/")

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["count"] == 0
        assert payload["next"] is None
        assert payload["previous"] is None
        assert payload["results"] == []
        assert payload["entries"] == []
