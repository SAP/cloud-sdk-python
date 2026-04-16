"""Utility functions for building OData filter and pagination parameters."""

from enum import Enum
from typing import Optional, Dict, List as TypingList
from urllib.parse import quote

from sap_cloud_sdk.destination.exceptions import DestinationOperationError


class Params(Enum):
    """Enumeration of possible query parameters."""

    FILTER = "$filter"
    SELECT = "$select"
    PAGE = "$page"
    PAGE_SIZE = "$pageSize"
    PAGE_COUNT = "$pageCount"
    ENTITY_COUNT = "$entityCount"
    INCLUDE_METADATA = "$includeMetadata"


def build_filter_param(property_name: str, values: TypingList[str]) -> str:
    """Build a 'Name in (...)' filter expression.

    Args:
        values: List of names to include in the filter.

    Returns:
        str: OData filter expression for name matching.
    """
    encoded_names = [f"'{quote(name)}'" for name in values]
    return f"{property_name} in ({', '.join(encoded_names)})"


def build_pagination_params(
    page: Optional[int],
    page_size: Optional[int],
    page_count: bool,
    entity_count: bool,
    has_select: bool,
    has_filter: bool,
) -> Dict[str, str]:
    """Validate and build pagination query parameters.

    Args:
        page: Page number (1-based).
        page_size: Number of items per page.
        page_count: Whether to include total page count.
        entity_count: Whether to include total entity count.
        has_select: Whether $select is being used.
        has_filter: Whether $filter is being used.

    Returns:
        Dict[str, str]: Pagination parameters.

    Raises:
        DestinationOperationError: If pagination configuration is invalid.
    """
    params: Dict[str, str] = {}

    if page is None:
        return params

    if has_select or has_filter:
        raise DestinationOperationError(
            f"{Params.PAGE.value} cannot be combined with {Params.SELECT.value} or {Params.FILTER.value}"
        )

    if page < 1:
        raise DestinationOperationError("page must be >= 1")

    params[Params.PAGE.value] = str(page)

    if page_size is not None:
        if not (1 <= page_size <= 1000):
            raise DestinationOperationError("page_size must be between 1 and 1000")

        params[Params.PAGE_SIZE.value] = str(page_size)

    if page_count:
        params[Params.PAGE_COUNT.value] = "true"

    if entity_count:
        params[Params.ENTITY_COUNT.value] = "true"

    return params
