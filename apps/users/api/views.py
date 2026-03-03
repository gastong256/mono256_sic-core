import structlog
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsAdminRole
from apps.users import services
from apps.users.api.serializers import UserRoleUpdateSerializer, UserSerializer, UserUpdateSerializer
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
        responses={200: UserSerializer(many=True)},
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

        paginator = PageNumberPagination()
        paginator.page_size = 25
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(UserSerializer(page, many=True).data)
