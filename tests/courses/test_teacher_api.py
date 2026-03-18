import datetime

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.companies import services as company_services
from apps.companies.models import Company
from apps.courses.models import Course, CourseDemoCompanyVisibility, CourseEnrollment
from apps.users.models import User
from tests.support.opening import seed_opening_chart


@pytest.mark.django_db
class TestTeacherCourseAggregatedEndpoints:
    def test_courses_support_all_and_selector_summary(self, api_client: APIClient):
        teacher = User.objects.create_user(
            username="teacher-course-selector", password="x", role=User.Role.TEACHER
        )
        Course.objects.create(name="Curso Uno", teacher=teacher)
        Course.objects.create(name="Curso Dos", teacher=teacher)

        api_client.force_authenticate(teacher)
        response = api_client.get("/api/v1/courses/?all=true&summary=selector")

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["count"] == 2
        assert payload["results"][0]["id"]
        assert "student_count" not in payload["results"][0]

    def test_companies_paginated_returns_students_only(self, api_client: APIClient):
        teacher = User.objects.create_user(
            username="teacher-api0", password="x", role=User.Role.TEACHER
        )
        student = User.objects.create_user(
            username="student-api0", password="x", role=User.Role.STUDENT
        )
        course = Course.objects.create(name="Curso API 0", teacher=teacher)
        CourseEnrollment.objects.create(course=course, student=student)
        Company.objects.create(name="Empresa Cero", owner=student)

        api_client.force_authenticate(teacher)
        response = api_client.get(f"/api/v1/teacher/courses/{course.id}/companies/")

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["count"] == 1
        assert payload["students"][0]["student_id"] == student.id
        assert "results" not in payload

    def test_companies_summary_returns_grouped_students(self, api_client: APIClient):
        teacher = User.objects.create_user(
            username="teacher-api", password="x", role=User.Role.TEACHER
        )
        student = User.objects.create_user(
            username="student-api", password="x", role=User.Role.STUDENT
        )
        course = Course.objects.create(name="Curso API", teacher=teacher)
        CourseEnrollment.objects.create(course=course, student=student)
        parents = seed_opening_chart()
        company_services.create_company_with_optional_opening(
            name="Empresa Uno",
            owner=student,
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
        response = api_client.get(f"/api/v1/teacher/courses/{course.id}/companies/summary/")

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["course_id"] == course.id
        assert len(payload["students"]) == 1
        assert payload["students"][0]["student_id"] == student.id
        assert len(payload["students"][0]["companies"]) == 1
        assert payload["students"][0]["companies"][0]["has_opening_entry"] is True
        assert payload["students"][0]["companies"][0]["accounting_ready"] is True
        assert payload["students"][0]["companies"][0]["opening_entry_id"] is not None

    def test_courses_overview_returns_aggregated_student_counts(self, api_client: APIClient):
        teacher = User.objects.create_user(
            username="teacher-overview", password="x", role=User.Role.TEACHER
        )
        student = User.objects.create_user(
            username="student-overview", password="x", role=User.Role.STUDENT
        )
        course = Course.objects.create(name="Curso Overview", teacher=teacher)
        CourseEnrollment.objects.create(course=course, student=student)
        Company.objects.create(name="Empresa Overview", owner=student)

        api_client.force_authenticate(teacher)
        response = api_client.get("/api/v1/teacher/courses/overview/")

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["courses"][0]["course_id"] == course.id
        assert payload["courses"][0]["students"][0]["student_id"] == student.id
        assert payload["courses"][0]["students"][0]["company_count"] == 1
        assert payload["courses"][0]["totals"]["company_count"] == 1

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
        assert payload["entries"] == []
        assert "results" not in payload

    def test_teacher_student_context_returns_company_summaries(self, api_client: APIClient):
        teacher = User.objects.create_user(
            username="teacher-context", password="x", role=User.Role.TEACHER
        )
        student = User.objects.create_user(
            username="student-context", password="x", role=User.Role.STUDENT
        )
        course = Course.objects.create(name="Curso Context", teacher=teacher)
        CourseEnrollment.objects.create(course=course, student=student)
        parents = seed_opening_chart()
        company = company_services.create_company_with_optional_opening(
            name="Empresa Context",
            owner=student,
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
            f"/api/v1/teacher/students/{student.id}/context/?company_id={company.id}"
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["student"]["id"] == student.id
        assert payload["selected_company_id"] == company.id
        assert payload["companies"][0]["journal_entry_count"] == 1
        assert payload["companies"][0]["has_opening_entry"] is True
        assert payload["companies"][0]["accounting_ready"] is True
        assert payload["companies"][0]["opening_entry_id"] is not None
        assert len(payload["journal_entries"]) == 1
        assert payload["journal_entries"][0]["source_type"] == "OPENING"

    def test_course_demo_company_visibility_can_be_listed_and_updated(
        self,
        api_client: APIClient,
    ):
        teacher = User.objects.create_user(
            username="teacher-demo-visibility",
            password="x",
            role=User.Role.TEACHER,
        )
        course = Course.objects.create(name="Curso Demo Visibility", teacher=teacher)
        demo_owner = User.objects.create_user(
            username="demo-owner-course",
            password="x",
            role=User.Role.ADMIN,
        )
        demo_company = Company.objects.create(
            name="Empresa Demo Curso",
            owner=demo_owner,
            is_demo=True,
            is_read_only=True,
        )

        api_client.force_authenticate(teacher)
        list_response = api_client.get(f"/api/v1/courses/{course.id}/demo-companies/")

        assert list_response.status_code == status.HTTP_200_OK
        payload = list_response.json()
        assert payload["course_id"] == course.id
        assert payload["demo_companies"][0]["company_id"] == demo_company.id
        assert payload["demo_companies"][0]["is_visible"] is False

        patch_response = api_client.patch(
            f"/api/v1/courses/{course.id}/demo-companies/{demo_company.id}/",
            {"is_visible": True},
            format="json",
        )

        assert patch_response.status_code == status.HTTP_200_OK
        assert patch_response.json()["company_id"] == demo_company.id
        assert patch_response.json()["is_visible"] is True
        assert (
            CourseDemoCompanyVisibility.objects.get(
                course=course,
                company=demo_company,
            ).is_visible
            is True
        )

    def test_teacher_demo_company_list_hides_unpublished_demos(self, api_client: APIClient):
        teacher = User.objects.create_user(
            username="teacher-demo-hidden-list",
            password="x",
            role=User.Role.TEACHER,
        )
        course = Course.objects.create(name="Curso Demo Hidden", teacher=teacher)
        demo_owner = User.objects.create_user(
            username="demo-owner-hidden-list",
            password="x",
            role=User.Role.ADMIN,
        )
        demo_company = Company.objects.create(
            name="Empresa Demo Oculta Global",
            owner=demo_owner,
            is_demo=True,
            is_read_only=True,
            is_published=False,
        )

        api_client.force_authenticate(teacher)
        response = api_client.get(f"/api/v1/courses/{course.id}/demo-companies/")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["demo_companies"] == []

        patch_response = api_client.patch(
            f"/api/v1/courses/{course.id}/demo-companies/{demo_company.id}/",
            {"is_visible": True},
            format="json",
        )
        assert patch_response.status_code == status.HTTP_404_NOT_FOUND
