from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.closing.api.serializers import (
    SimplifiedClosingExecuteSerializer,
    SimplifiedClosingPreviewSerializer,
    SimplifiedClosingRequestSerializer,
    SimplifiedClosingStateSerializer,
)
from apps.closing import services
from apps.companies import selectors as company_selectors


class ClosingStateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="get_company_closing_state",
        summary="Get simplified closing state for a company",
        responses={200: SimplifiedClosingStateSerializer},
        tags=["closing"],
    )
    def get(self, request: Request, company_id: int) -> Response:
        company = company_selectors.get_company(pk=company_id, user=request.user)
        data = services.get_closing_state(company=company)
        return Response(SimplifiedClosingStateSerializer(data).data)


class ClosingPreviewView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="preview_company_simplified_closing",
        summary="Preview the simplified accounting closing plan",
        request=SimplifiedClosingRequestSerializer,
        responses={
            200: SimplifiedClosingPreviewSerializer,
            403: OpenApiResponse(description="Permission denied"),
            409: OpenApiResponse(description="Closing cannot be prepared for the selected dates"),
        },
        tags=["closing"],
    )
    def post(self, request: Request, company_id: int) -> Response:
        company = company_selectors.get_company(pk=company_id, user=request.user)
        services.assert_can_manage_company_closing(actor=request.user, company=company)
        serializer = SimplifiedClosingRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = services.build_simplified_closing_plan(
            company=company, data=serializer.validated_data
        )
        return Response(SimplifiedClosingPreviewSerializer(data).data)


class ClosingExecuteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="execute_company_simplified_closing",
        summary="Execute the simplified accounting closing",
        request=SimplifiedClosingRequestSerializer,
        responses={
            200: SimplifiedClosingExecuteSerializer,
            403: OpenApiResponse(description="Permission denied"),
            409: OpenApiResponse(description="Closing cannot be executed for the selected dates"),
        },
        tags=["closing"],
    )
    def post(self, request: Request, company_id: int) -> Response:
        company = company_selectors.get_company(pk=company_id, user=request.user)
        serializer = SimplifiedClosingRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = services.execute_simplified_closing(
            company=company,
            actor=request.user,
            data=serializer.validated_data,
        )
        return Response(SimplifiedClosingExecuteSerializer(data).data)
