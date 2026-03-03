import structlog
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users import services
from apps.users.api.serializers import UserSerializer, UserUpdateSerializer

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
