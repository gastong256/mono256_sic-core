import structlog
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.companies import selectors, services
from apps.companies.api.serializers import CompanySerializer, CompanyWriteSerializer

logger = structlog.get_logger(__name__)


@extend_schema_view(
    list=extend_schema(
        operation_id="list_companies",
        summary="List companies",
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
        request=CompanyWriteSerializer,
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
    """
    CRUD ViewSet for Company.

    Teachers see and can manage all companies.
    Students can only create companies for themselves and manage their own.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return companies visible to the requesting user."""
        # drf-spectacular calls get_queryset() during schema generation with a fake view.
        if getattr(self, "swagger_fake_view", False):
            from apps.companies.models import Company

            return Company.objects.none()
        return selectors.list_companies(user=self.request.user)

    def get_serializer_class(self):
        """Use write serializer for mutations; read serializer for reads."""
        if self.action in ("create", "update", "partial_update"):
            return CompanyWriteSerializer
        return CompanySerializer

    def get_object(self):
        """Retrieve company, enforcing ownership rules via selector."""
        return selectors.get_company(pk=self.kwargs["pk"], user=self.request.user)

    def create(self, request: Request, *args, **kwargs) -> Response:
        """Create a new company owned by the requesting student."""
        serializer = CompanyWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        company = services.create_company(
            **serializer.validated_data,
            owner=request.user,
        )
        logger.info("company_created", company_id=company.pk, owner=request.user.username)
        return Response(CompanySerializer(company).data, status=status.HTTP_201_CREATED)

    def update(self, request: Request, *args, **kwargs) -> Response:
        """Update an existing company (owner or teacher)."""
        partial = kwargs.pop("partial", False)
        company = self.get_object()

        serializer = CompanyWriteSerializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        company = services.update_company(company=company, **serializer.validated_data)
        logger.info("company_updated", company_id=company.pk)
        return Response(CompanySerializer(company).data)

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """Delete a company (owner or teacher)."""
        company = self.get_object()
        services.delete_company(company=company)
        logger.info("company_deleted", company_id=kwargs["pk"])
        return Response(status=status.HTTP_204_NO_CONTENT)
