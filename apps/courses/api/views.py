import datetime

import structlog
from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import paginate_queryset
from apps.common.permissions import IsTeacherOrAdminRole
from apps.common.role_resolution import resolve_teacher_for_actor
from apps.companies.models import Company
from apps.courses import selectors, services
from apps.courses.api.serializers import (
    AvailableStudentsPaginatedResponseSerializer,
    AvailableStudentSerializer,
    CourseSerializer,
    CoursePaginatedResponseSerializer,
    CourseWriteSerializer,
    EnrollmentPaginatedResponseSerializer,
    EnrollmentCreateSerializer,
    EnrollmentSerializer,
    TeacherCourseCompaniesPaginatedResponseSerializer,
    TeacherCourseJournalEntriesResponseSerializer,
    TeacherCourseJournalEntrySerializer,
)
from apps.courses.models import CourseEnrollment
from apps.journal.models import JournalEntry
from apps.users.models import User

logger = structlog.get_logger(__name__)


def _resolve_course_teacher(*, request_user: User, teacher_id: int | None) -> User:
    return resolve_teacher_for_actor(
        actor=request_user,
        teacher_id=teacher_id,
        missing_teacher_id_message="teacher_id is required for admin course creation.",
    )


class CourseListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsTeacherOrAdminRole]

    @extend_schema(
        operation_id="courses_list",
        tags=["courses"],
        parameters=[OpenApiParameter(name="page", type=int, required=False)],
        responses={200: CoursePaginatedResponseSerializer},
    )
    def get(self, request: Request) -> Response:
        courses_qs = selectors.list_courses(user=request.user)
        paginator, page = paginate_queryset(request=request, queryset=courses_qs)
        data = CourseSerializer(page, many=True).data
        return paginator.get_paginated_response(data)

    @extend_schema(
        operation_id="courses_create",
        tags=["courses"],
        request=CourseWriteSerializer,
        responses={201: CourseSerializer, 400: OpenApiResponse(description="Validation error")},
    )
    def post(self, request: Request) -> Response:
        serializer = CourseWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        teacher = _resolve_course_teacher(
            request_user=request.user,
            teacher_id=serializer.validated_data.get("teacher_id"),
        )
        course = services.create_course(
            teacher=teacher,
            name=serializer.validated_data["name"],
            code=serializer.validated_data.get("code"),
        )
        logger.info(
            "course_created", course_id=course.pk, teacher_id=teacher.pk, actor_id=request.user.pk
        )
        return Response(CourseSerializer(course).data, status=status.HTTP_201_CREATED)


class CourseDetailView(APIView):
    permission_classes = [IsAuthenticated, IsTeacherOrAdminRole]

    @extend_schema(
        operation_id="courses_retrieve", tags=["courses"], responses={200: CourseSerializer}
    )
    def get(self, request: Request, course_id: int) -> Response:
        course = selectors.get_course(pk=course_id, user=request.user)
        return Response(CourseSerializer(course).data)

    @extend_schema(
        operation_id="courses_partial_update",
        tags=["courses"],
        request=CourseWriteSerializer,
        responses={200: CourseSerializer},
    )
    def patch(self, request: Request, course_id: int) -> Response:
        course = selectors.get_course(pk=course_id, user=request.user)

        serializer = CourseWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated = services.update_course(
            course=course,
            name=serializer.validated_data.get("name"),
            code=serializer.validated_data.get("code"),
        )
        logger.info("course_updated", course_id=updated.pk, actor_id=request.user.pk)
        return Response(CourseSerializer(updated).data)

    @extend_schema(
        operation_id="courses_destroy",
        tags=["courses"],
        responses={204: OpenApiResponse(description="No content")},
    )
    def delete(self, request: Request, course_id: int) -> Response:
        course = selectors.get_course(pk=course_id, user=request.user)
        services.delete_course(course=course)
        logger.info("course_deleted", course_id=course_id, actor_id=request.user.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CourseEnrollmentCreateView(APIView):
    permission_classes = [IsAuthenticated, IsTeacherOrAdminRole]

    @extend_schema(
        operation_id="courses_enrollments_list",
        tags=["courses"],
        parameters=[OpenApiParameter(name="page", type=int, required=False)],
        responses={200: EnrollmentPaginatedResponseSerializer},
    )
    def get(self, request: Request, course_id: int) -> Response:
        course = selectors.get_course(pk=course_id, user=request.user)
        enrollments_qs = (
            CourseEnrollment.objects.filter(course=course)
            .select_related("student")
            .order_by("student__username")
        )
        paginator, page = paginate_queryset(request=request, queryset=enrollments_qs)
        data = EnrollmentSerializer(page, many=True).data
        return paginator.get_paginated_response(data)

    @extend_schema(
        operation_id="courses_enrollments_create",
        tags=["courses"],
        request=EnrollmentCreateSerializer,
        responses={201: EnrollmentSerializer},
    )
    def post(self, request: Request, course_id: int) -> Response:
        from rest_framework.exceptions import ValidationError

        course = selectors.get_course(pk=course_id, user=request.user)

        serializer = EnrollmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            student = User.objects.get(pk=serializer.validated_data["student_id"])
        except User.DoesNotExist as exc:
            raise ValidationError({"student_id": "Student not found."}) from exc

        enrollment = services.enroll_student(course=course, student=student)
        logger.info(
            "course_student_enrolled",
            course_id=course.pk,
            student_id=student.pk,
            actor_id=request.user.pk,
        )
        return Response(EnrollmentSerializer(enrollment).data, status=status.HTTP_201_CREATED)


class CourseEnrollmentDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsTeacherOrAdminRole]

    @extend_schema(
        operation_id="courses_enrollments_destroy",
        tags=["courses"],
        responses={204: OpenApiResponse(description="No content")},
    )
    def delete(self, request: Request, course_id: int, student_id: int) -> Response:
        course = selectors.get_course(pk=course_id, user=request.user)

        try:
            student = User.objects.get(pk=student_id)
        except User.DoesNotExist:
            from rest_framework.exceptions import NotFound

            raise NotFound("Student not found.")

        services.unenroll_student(course=course, student=student)
        logger.info(
            "course_student_unenrolled",
            course_id=course.pk,
            student_id=student.pk,
            actor_id=request.user.pk,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class TeacherCourseCompaniesView(APIView):
    permission_classes = [IsAuthenticated, IsTeacherOrAdminRole]

    @extend_schema(
        operation_id="teacher_courses_companies_retrieve",
        tags=["teacher"],
        parameters=[OpenApiParameter(name="page", type=int, required=False)],
        responses={200: TeacherCourseCompaniesPaginatedResponseSerializer},
    )
    def get(self, request: Request, course_id: int) -> Response:
        course = selectors.get_course(pk=course_id, user=request.user)

        enrollments_qs = (
            CourseEnrollment.objects.filter(course=course)
            .select_related("student")
            .order_by("student__username")
        )
        paginator, page = paginate_queryset(request=request, queryset=enrollments_qs)
        student_ids = [e.student_id for e in page]

        companies = (
            Company.objects.filter(owner_id__in=student_ids)
            .select_related("owner")
            .order_by("owner__username", "name")
        )

        companies_by_student: dict[int, list[dict]] = {sid: [] for sid in student_ids}
        for company in companies:
            companies_by_student[company.owner_id].append(
                {
                    "id": company.id,
                    "name": company.name,
                    "tax_id": company.tax_id,
                    "created_at": company.created_at,
                }
            )

        data = [
            {
                "student_id": enrollment.student_id,
                "student_username": enrollment.student.username,
                "student_full_name": enrollment.student.get_full_name(),
                "companies": companies_by_student.get(enrollment.student_id, []),
            }
            for enrollment in page
        ]
        payload = {
            "course_id": course.id,
            "course_name": course.name,
            "count": paginator.page.paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": data,
        }
        response_serializer = TeacherCourseCompaniesPaginatedResponseSerializer(payload)
        return Response(response_serializer.data)


class TeacherCourseJournalEntriesView(APIView):
    permission_classes = [IsAuthenticated, IsTeacherOrAdminRole]

    @extend_schema(
        operation_id="teacher_courses_journal_entries_retrieve",
        tags=["teacher"],
        parameters=[
            OpenApiParameter(name="date_from", type=str, required=False),
            OpenApiParameter(name="date_to", type=str, required=False),
            OpenApiParameter(name="student_id", type=int, required=False),
            OpenApiParameter(name="company_id", type=int, required=False),
            OpenApiParameter(name="page", type=int, required=False),
        ],
        responses={200: TeacherCourseJournalEntriesResponseSerializer},
    )
    def get(self, request: Request, course_id: int) -> Response:
        from rest_framework.exceptions import ValidationError

        course = selectors.get_course(pk=course_id, user=request.user)
        enrollments = CourseEnrollment.objects.filter(course=course).values_list(
            "student_id", flat=True
        )

        qs = (
            JournalEntry.objects.filter(company__owner_id__in=enrollments)
            .select_related("company", "company__owner", "created_by")
            .prefetch_related("lines__account", "reversed_by")
            .order_by("-date", "-entry_number")
        )

        date_from = request.query_params.get("date_from")
        if date_from:
            try:
                qs = qs.filter(date__gte=datetime.date.fromisoformat(date_from))
            except ValueError:
                raise ValidationError({"date_from": "Invalid date format. Use YYYY-MM-DD."})

        date_to = request.query_params.get("date_to")
        if date_to:
            try:
                qs = qs.filter(date__lte=datetime.date.fromisoformat(date_to))
            except ValueError:
                raise ValidationError({"date_to": "Invalid date format. Use YYYY-MM-DD."})

        student_id = request.query_params.get("student_id")
        if student_id:
            qs = qs.filter(company__owner_id=student_id)

        company_id = request.query_params.get("company_id")
        if company_id:
            qs = qs.filter(company_id=company_id)

        paginator, page = paginate_queryset(request=request, queryset=qs)
        data = TeacherCourseJournalEntrySerializer(page, many=True).data
        return paginator.get_paginated_response(data)


class TeacherAvailableStudentsView(APIView):
    permission_classes = [IsAuthenticated, IsTeacherOrAdminRole]

    @extend_schema(
        operation_id="teacher_students_available_retrieve",
        tags=["teacher"],
        parameters=[
            OpenApiParameter(name="course_id", type=int, required=True),
            OpenApiParameter(name="search", type=str, required=False),
            OpenApiParameter(name="page", type=int, required=False),
        ],
        responses={200: AvailableStudentsPaginatedResponseSerializer},
    )
    def get(self, request: Request) -> Response:
        from rest_framework.exceptions import ValidationError

        course_id_raw = request.query_params.get("course_id")
        if not course_id_raw:
            raise ValidationError({"course_id": "course_id is required."})
        try:
            course_id = int(course_id_raw)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"course_id": "course_id must be an integer."}) from exc

        selectors.get_course(pk=course_id, user=request.user)

        students_qs = User.objects.filter(
            role=User.Role.STUDENT,
            course_enrollment__isnull=True,
        ).order_by("username")

        search = request.query_params.get("search")
        if search:
            students_qs = students_qs.filter(
                Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )

        paginator, page = paginate_queryset(request=request, queryset=students_qs)
        data = AvailableStudentSerializer(page, many=True).data
        return paginator.get_paginated_response(data)
