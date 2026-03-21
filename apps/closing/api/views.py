from drf_spectacular.utils import OpenApiResponse, extend_schema
from drf_spectacular.types import OpenApiTypes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.closing.exports import build_closing_snapshot_workbook
from apps.closing.api.serializers import (
    ClosingSnapshotSerializer,
    CurrentBookBalancesParamsSerializer,
    CurrentBookBalancesSerializer,
    LogicalExerciseListSerializer,
    SimplifiedClosingExecuteSerializer,
    SimplifiedClosingPreviewSerializer,
    SimplifiedClosingRequestSerializer,
    SimplifiedClosingStateSerializer,
)
from apps.closing import selectors, services
from apps.companies import selectors as company_selectors
from apps.reports.exports.common import ensure_excel_dependency, workbook_response


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


class CurrentBookBalancesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="get_company_current_book_balances",
        summary="Get current book balances for cash and inventory",
        parameters=[CurrentBookBalancesParamsSerializer],
        responses={
            200: CurrentBookBalancesSerializer,
            400: OpenApiResponse(description="Invalid query parameters"),
            409: OpenApiResponse(
                description="Company must be opened before book balances are available"
            ),
        },
        tags=["closing"],
    )
    def get(self, request: Request, company_id: int) -> Response:
        company = company_selectors.get_company(pk=company_id, user=request.user)
        params = CurrentBookBalancesParamsSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        data = services.get_current_book_balances(
            company=company,
            date_to=params.validated_data.get("date_to"),
        )
        return Response(CurrentBookBalancesSerializer(data).data)


class LogicalExerciseListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="list_company_logical_exercises",
        summary="List inferred logical fiscal exercises for a company",
        responses={200: LogicalExerciseListSerializer},
        tags=["closing"],
    )
    def get(self, request: Request, company_id: int) -> Response:
        company = company_selectors.get_company(pk=company_id, user=request.user)
        exercises = selectors.list_logical_exercises(company=company)
        current = selectors.get_current_logical_exercise(company=company)
        data = {
            "company_id": company.id,
            "company": company.name,
            "current_exercise_id": current.exercise_id if current else None,
            "exercises": [selectors.serialize_logical_exercise(exercise) for exercise in exercises],
        }
        return Response(LogicalExerciseListSerializer(data).data)


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


class LatestClosingSnapshotView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="get_latest_company_closing_snapshot",
        summary="Get the latest immutable closing snapshot for a company",
        responses={200: ClosingSnapshotSerializer},
        tags=["closing"],
    )
    def get(self, request: Request, company_id: int) -> Response:
        company = company_selectors.get_company(pk=company_id, user=request.user)
        snapshot = selectors.get_latest_snapshot(company=company)
        if snapshot is None:
            from rest_framework.exceptions import NotFound

            raise NotFound("No closing snapshot exists for this company.")
        data = services.serialize_snapshot(snapshot=snapshot)
        return Response(ClosingSnapshotSerializer(data).data)


class LatestClosingSnapshotExcelExportView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="export_latest_company_closing_snapshot_xlsx",
        summary="Export the latest immutable closing snapshot as XLSX",
        responses={
            200: OpenApiResponse(description="XLSX file", response=OpenApiTypes.BINARY),
        },
        tags=["closing"],
    )
    def get(self, request: Request, company_id: int) -> Response:
        ensure_excel_dependency()
        company = company_selectors.get_company(pk=company_id, user=request.user)
        snapshot = selectors.get_latest_snapshot(company=company)
        if snapshot is None:
            from rest_framework.exceptions import NotFound

            raise NotFound("No closing snapshot exists for this company.")
        data = services.serialize_snapshot(snapshot=snapshot)
        artifact = build_closing_snapshot_workbook(snapshot=data)
        filename = f"cierre_contable_{company.id}_{snapshot.closing_date.isoformat()}.xlsx"
        return workbook_response(artifact=artifact, filename=filename)


class ClosingSnapshotDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="get_company_closing_snapshot",
        summary="Get an immutable closing snapshot by ID",
        responses={200: ClosingSnapshotSerializer},
        tags=["closing"],
    )
    def get(self, request: Request, company_id: int, snapshot_id: int) -> Response:
        company = company_selectors.get_company(pk=company_id, user=request.user)
        from apps.closing.models import ClosingSnapshot
        from rest_framework.exceptions import NotFound

        try:
            snapshot = selectors.get_snapshot(company=company, snapshot_id=snapshot_id)
        except ClosingSnapshot.DoesNotExist as exc:
            raise NotFound("Closing snapshot not found.") from exc
        data = services.serialize_snapshot(snapshot=snapshot)
        return Response(ClosingSnapshotSerializer(data).data)


class ClosingSnapshotExcelExportView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="export_company_closing_snapshot_xlsx",
        summary="Export an immutable closing snapshot as XLSX",
        responses={
            200: OpenApiResponse(description="XLSX file", response=OpenApiTypes.BINARY),
        },
        tags=["closing"],
    )
    def get(self, request: Request, company_id: int, snapshot_id: int) -> Response:
        ensure_excel_dependency()
        company = company_selectors.get_company(pk=company_id, user=request.user)
        from apps.closing.models import ClosingSnapshot
        from rest_framework.exceptions import NotFound

        try:
            snapshot = selectors.get_snapshot(company=company, snapshot_id=snapshot_id)
        except ClosingSnapshot.DoesNotExist as exc:
            raise NotFound("Closing snapshot not found.") from exc
        data = services.serialize_snapshot(snapshot=snapshot)
        artifact = build_closing_snapshot_workbook(snapshot=data)
        filename = (
            f"cierre_contable_{company.id}_{snapshot.closing_date.isoformat()}_{snapshot.id}.xlsx"
        )
        return workbook_response(artifact=artifact, filename=filename)
