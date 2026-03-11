from __future__ import annotations

from typing import Any

from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request


def paginate_queryset(*, request: Request, queryset: Any, page_size: int = 25) -> tuple[PageNumberPagination, Any]:
    paginator = PageNumberPagination()
    paginator.page_size = page_size
    page = paginator.paginate_queryset(queryset, request)
    return paginator, page
