import uuid

import structlog
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.example import selectors, services
from apps.example.api.serializers import ItemCreateSerializer, ItemSerializer
from apps.example.models import Item

logger = structlog.get_logger(__name__)


class PingView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="ping",
        summary="Health ping",
        responses={200: {"type": "object", "properties": {"message": {"type": "string"}}}},
        tags=["utility"],
    )
    def get(self, request: Request) -> Response:
        return Response({"message": "pong"})


class ItemCreateView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="create_item",
        summary="Create item",
        request=ItemCreateSerializer,
        responses={
            201: ItemSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
        tags=["items"],
    )
    def post(self, request: Request) -> Response:
        serializer = ItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        item = services.create_item(**serializer.validated_data)
        logger.info("item_created", item_id=str(item.id), name=item.name)

        return Response(ItemSerializer(item).data, status=status.HTTP_201_CREATED)


class ItemDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="get_item",
        summary="Get item by ID",
        responses={
            200: ItemSerializer,
            404: OpenApiResponse(description="Item not found"),
        },
        tags=["items"],
    )
    def get(self, request: Request, pk: uuid.UUID) -> Response:
        try:
            item = selectors.get_item(pk)
        except Item.DoesNotExist:
            raise NotFound(detail="Item not found.")

        return Response(ItemSerializer(item).data)
