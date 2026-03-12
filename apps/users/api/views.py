import structlog
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.exceptions import NotFound, Throttled
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import paginate_queryset
from apps.common.permissions import IsAdminRole, IsTeacherOrAdminRole
from apps.users import services
from apps.users.api.serializers import (
    RegistrationCodeInfoSerializer,
    UserListPaginatedSerializer,
    UserRegisterSerializer,
    UserRoleUpdateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from apps.users.models import User

logger = structlog.get_logger(__name__)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="get_me",
        summary="Get current user",
        responses={200: UserSerializer},
        tags=["auth"],
    )
    def get(self, request: Request) -> Response:
        return Response(UserSerializer(request.user).data)

    @extend_schema(
        operation_id="update_me",
        summary="Update current user profile",
        request=UserUpdateSerializer,
        responses={200: UserSerializer},
        tags=["auth"],
    )
    def patch(self, request: Request) -> Response:
        serializer = UserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.update_me(user=request.user, **serializer.validated_data)
        logger.info("me_updated", user_id=user.pk)
        return Response(UserSerializer(user).data)


class RegisterView(APIView):
    permission_classes = []
    throttle_scope = "auth_register"

    @extend_schema(
        operation_id="register_student",
        summary="Register new student user",
        request=UserRegisterSerializer,
        responses={
            201: UserSerializer,
            400: OpenApiResponse(description="Validation error"),
            429: OpenApiResponse(description="Rate limited or cooldown active"),
        },
        tags=["auth"],
    )
    def post(self, request: Request) -> Response:
        serializer = UserRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip = request.META.get("REMOTE_ADDR", "unknown")
        username = serializer.validated_data.get("username", "")

        retry_after = services.check_registration_limits(ip=ip, username=username)
        if retry_after is not None:
            raise Throttled(
                wait=retry_after, detail="Too many registration attempts. Try again later."
            )

        try:
            user = services.register_student_user(**serializer.validated_data)
        except Exception:
            cooldown = services.register_failure(ip=ip, username=username)
            logger.warning(
                "registration_failed",
                username=username,
                ip=ip,
                cooldown=cooldown,
            )
            raise

        services.register_success(ip=ip, username=username)
        logger.info("user_registered", user_id=user.pk, username=user.username, ip=ip)
        return Response(UserSerializer(user).data, status=201)


class UserRoleUpdateView(APIView):
    permission_classes = [IsAdminRole]

    @extend_schema(
        operation_id="admin_update_user_role",
        summary="Update user role",
        request=UserRoleUpdateSerializer,
        responses={200: UserSerializer},
        tags=["admin"],
    )
    def patch(self, request: Request, user_id: int) -> Response:
        serializer = UserRoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise NotFound(detail="User not found.")

        user = services.set_user_role(user=user, role=serializer.validated_data["role"])
        logger.info(
            "user_role_updated",
            actor_id=request.user.pk,
            target_user_id=user.pk,
            role=user.role,
        )
        return Response(UserSerializer(user).data)


class UserListView(APIView):
    permission_classes = [IsAdminRole]

    @extend_schema(
        operation_id="admin_list_users",
        summary="List users",
        parameters=[
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Pagination page number.",
            ),
            OpenApiParameter(
                name="role",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                enum=[User.Role.ADMIN, User.Role.TEACHER, User.Role.STUDENT],
                description="Filter users by role.",
            ),
            OpenApiParameter(
                name="search",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Case-insensitive username search.",
            ),
        ],
        responses={200: UserListPaginatedSerializer},
        tags=["admin"],
    )
    def get(self, request: Request) -> Response:
        qs = User.objects.all().order_by("-date_joined").select_related("course_enrollment")

        role = request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)

        search = request.query_params.get("search")
        if search:
            qs = qs.filter(username__icontains=search)

        paginator, page = paginate_queryset(request=request, queryset=qs, page_size=20)
        return paginator.get_paginated_response(UserSerializer(page, many=True).data)


class TeacherRegistrationCodeInfoView(APIView):
    permission_classes = [IsAuthenticated, IsTeacherOrAdminRole]

    @extend_schema(
        operation_id="teacher_get_registration_code",
        summary="Get current registration code",
        responses={200: RegistrationCodeInfoSerializer},
        tags=["teacher"],
    )
    def get(self, request: Request) -> Response:
        if request.user.role not in {User.Role.TEACHER, User.Role.ADMIN}:
            raise NotFound(detail="Not found.")
        info = services.get_current_registration_code_info()
        return Response(RegistrationCodeInfoSerializer(info).data)


class AdminRegistrationCodeInfoView(APIView):
    permission_classes = [IsAdminRole]

    @extend_schema(
        operation_id="admin_get_registration_code",
        summary="Get current registration code",
        responses={200: RegistrationCodeInfoSerializer},
        tags=["admin"],
    )
    def get(self, request: Request) -> Response:
        info = services.get_current_registration_code_info()
        return Response(RegistrationCodeInfoSerializer(info).data)


class RegistrationCodeRotateView(APIView):
    permission_classes = [IsAdminRole]

    @extend_schema(
        operation_id="rotate_registration_code",
        summary="Rotate registration code",
        request=None,
        responses={200: RegistrationCodeInfoSerializer},
        tags=["admin"],
    )
    def post(self, request: Request) -> Response:
        info = services.rotate_registration_code()
        logger.info("registration_code_rotated", actor_id=request.user.pk)
        return Response(RegistrationCodeInfoSerializer(info).data)
