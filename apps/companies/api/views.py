import structlog
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.pagination import paginate_queryset
from apps.common.permissions import IsAdminRole
from apps.common.query_params import is_truthy_param
from apps.companies import selectors, services
from apps.companies.api.serializers import (
    CompanyCreateSerializer,
    DemoPublicationSerializer,
    CompanyOpeningEntrySerializer,
    CompanySelectorSerializer,
    CompanySerializer,
    CompanyWriteSerializer,
)
from apps.journal.api.serializers import JournalEntryDetailSerializer

logger = structlog.get_logger(__name__)


@extend_schema_view(
    list=extend_schema(
        operation_id="list_companies",
        summary="List companies",
        parameters=[
            OpenApiParameter(name="page", type=int, required=False),
            OpenApiParameter(
                name="all",
                type=bool,
                required=False,
                description="Return the full list in one response.",
            ),
            OpenApiParameter(
                name="summary",
                type=str,
                required=False,
                enum=["selector"],
                description="Return a lightweight item shape for selectors.",
            ),
        ],
        responses={
            200: CompanySerializer(many=True),
        },
        tags=["companies"],
    ),
    retrieve=extend_schema(
        operation_id="get_company",
        summary="Retrieve a company",
        tags=["companies"],
    ),
    create=extend_schema(
        operation_id="create_company",
        summary="Create a company",
        request=CompanyCreateSerializer,
        responses={
            201: CompanySerializer,
            400: OpenApiResponse(description="Validation error"),
        },
        tags=["companies"],
    ),
    update=extend_schema(
        operation_id="update_company",
        summary="Update a company",
        request=CompanyWriteSerializer,
        responses={
            200: CompanySerializer,
            400: OpenApiResponse(description="Validation error"),
            403: OpenApiResponse(description="Permission denied"),
            409: OpenApiResponse(description="Read-only demo company"),
        },
        tags=["companies"],
    ),
    partial_update=extend_schema(
        operation_id="partial_update_company",
        summary="Partially update a company",
        request=CompanyWriteSerializer,
        responses={
            200: CompanySerializer,
            400: OpenApiResponse(description="Validation error"),
            403: OpenApiResponse(description="Permission denied"),
            409: OpenApiResponse(description="Read-only demo company"),
        },
        tags=["companies"],
    ),
    destroy=extend_schema(
        operation_id="delete_company",
        summary="Delete a company",
        responses={
            204: OpenApiResponse(description="No content"),
            403: OpenApiResponse(description="Permission denied"),
            409: OpenApiResponse(description="Company has protected accounting records"),
        },
        tags=["companies"],
    ),
)
class CompanyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # drf-spectacular calls this without a real request user while building schema.
        if getattr(self, "swagger_fake_view", False):
            from apps.companies.models import Company

            return Company.objects.none()
        return selectors.list_companies(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return CompanyCreateSerializer
        if self.action in ("update", "partial_update"):
            return CompanyWriteSerializer
        return CompanySerializer

    def list(self, request: Request, *args, **kwargs) -> Response:
        queryset = self.get_queryset()
        summary = request.query_params.get("summary")
        serializer_class = CompanySelectorSerializer if summary == "selector" else CompanySerializer

        if is_truthy_param(request.query_params.get("all")):
            data = serializer_class(queryset, many=True).data
            return Response(
                {
                    "count": len(data),
                    "next": None,
                    "previous": None,
                    "results": data,
                }
            )

        paginator, page = paginate_queryset(request=request, queryset=queryset)
        data = serializer_class(page, many=True).data
        return Response(
            {
                "count": paginator.page.paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "results": data,
            }
        )

    def get_object(self):
        return selectors.get_company(pk=self.kwargs["pk"], user=self.request.user)

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = CompanyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        company = services.create_company_with_optional_opening(
            **serializer.validated_data,
            owner=request.user,
        )
        logger.info("company_created", company_id=company.pk, owner=request.user.username)
        return Response(CompanySerializer(company).data, status=status.HTTP_201_CREATED)

    def update(self, request: Request, *args, **kwargs) -> Response:
        partial = kwargs.pop("partial", False)
        company = self.get_object()

        serializer = CompanyWriteSerializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        company = services.update_company(company=company, **serializer.validated_data)
        logger.info("company_updated", company_id=company.pk)
        return Response(CompanySerializer(company).data)

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        company = self.get_object()
        services.delete_company(company=company)
        logger.info("company_deleted", company_id=kwargs["pk"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        operation_id="create_company_opening_entry",
        summary="Create the opening entry for an existing company",
        request=CompanyOpeningEntrySerializer,
        responses={
            201: JournalEntryDetailSerializer,
            400: OpenApiResponse(description="Validation error"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Company not found"),
            409: OpenApiResponse(
                description="Company already opened, already has entries, or is read-only"
            ),
        },
        tags=["companies"],
    )
    @action(detail=True, methods=["post"], url_path="opening-entry")
    def opening_entry(self, request: Request, pk: str | None = None) -> Response:
        company = self.get_object()
        serializer = CompanyOpeningEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        entry = services.create_company_opening_entry(
            company=company,
            actor=request.user,
            opening_entry=serializer.validated_data,
        )
        logger.info(
            "company_opening_entry_created",
            company_id=company.pk,
            entry_id=entry.pk,
            user=request.user.username,
        )
        from apps.journal import selectors as journal_selectors

        entry_with_lines = journal_selectors.get_journal_entry(pk=entry.pk, company=company)
        return Response(
            JournalEntryDetailSerializer(entry_with_lines).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(
        operation_id="set_demo_company_publication",
        summary="Publish or unpublish a demo company",
        request=DemoPublicationSerializer,
        responses={
            200: CompanySerializer,
            400: OpenApiResponse(description="Validation error"),
            403: OpenApiResponse(description="Admin role required"),
            404: OpenApiResponse(description="Company not found"),
        },
        tags=["companies"],
    )
    @action(
        detail=True,
        methods=["patch"],
        url_path="demo-publication",
        permission_classes=[IsAuthenticated, IsAdminRole],
    )
    def demo_publication(self, request: Request, pk: str | None = None) -> Response:
        company = self.get_object()
        serializer = DemoPublicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        company = services.set_demo_publication(
            company=company,
            is_published=serializer.validated_data["is_published"],
        )
        logger.info(
            "demo_company_publication_updated",
            company_id=company.pk,
            is_published=company.is_published,
            actor=request.user.username,
        )
        return Response(CompanySerializer(company).data)
