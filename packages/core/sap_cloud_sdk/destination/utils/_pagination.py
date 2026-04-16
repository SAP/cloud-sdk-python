"""Pagination utilities for Destination Service API responses.

This module provides:
- PaginationInfo: Dataclass for pagination metadata from response headers
- PagedResult: Generic container for paged list results
- parse_pagination_headers: Helper to extract pagination info from HTTP response headers
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, TypeVar, Generic
import re

from requests import Response

T = TypeVar("T")


@dataclass
class PaginationInfo:
    """Pagination information returned by the API.

    This class contains pagination metadata returned in response headers
    when pagination is enabled via ListOptions.

    Attributes:
        page_count: Total number of pages (from Page-Count header)
        entity_count: Total number of entities (from Entity-Count header)
        next_page_url: URL for the next page (from Link header, rel='next')
        previous_page_url: URL for the previous page (from Link header, rel='previous')
    """

    page_count: Optional[int] = None
    entity_count: Optional[int] = None
    next_page_url: Optional[str] = None
    previous_page_url: Optional[str] = None


@dataclass
class PagedResult(Generic[T]):
    """Paged result containing items and pagination information.

    Generic container for list results that includes both the items
    and pagination metadata when pagination is requested.

    Type Parameters:
        T: The type of items in the result list

    Attributes:
        items: List of items (e.g., Destination, Certificate, Fragment)
        pagination: Pagination information (None if pagination not requested)

    Example:
        ```python
        from sap_cloud_sdk.destination import create_client
        from sap_cloud_sdk.destination._models import ListOptions

        client = create_client()
        result = client.list_instance_destinations(
            filter=ListOptions(page=1, page_size=10, page_count=True)
        )
        print(f"Items: {len(result.items)}")
        if result.pagination:
            print(f"Total pages: {result.pagination.page_count}")
            print(f"Total items: {result.pagination.entity_count}")
        ```
    """

    items: List[T]
    pagination: Optional[PaginationInfo] = None


def parse_pagination_headers(response: Response) -> Optional[PaginationInfo]:
    """Parse pagination information from response headers.

    Extracts pagination metadata from the response headers when pagination
    parameters were requested in the API call.

    Args:
        response: HTTP response object from a list operation

    Returns:
        PaginationInfo object if pagination headers are present, None otherwise

    Example response headers:
        Page-Count: 5
        Entity-Count: 47
        Link: </subaccountDestinations?$page=1&$pageSize=10>; rel='previous',
              </subaccountDestinations?$page=3&$pageSize=10>; rel='next'
    """
    headers = response.headers

    # Check if any pagination headers are present
    if not any(h in headers for h in ["Page-Count", "Entity-Count", "Link"]):
        return None

    pagination = PaginationInfo()

    # Parse Page-Count header
    if "Page-Count" in headers:
        try:
            pagination.page_count = int(headers["Page-Count"])
        except (ValueError, TypeError):
            pass

    # Parse Entity-Count header
    if "Entity-Count" in headers:
        try:
            pagination.entity_count = int(headers["Entity-Count"])
        except (ValueError, TypeError):
            pass

    # Parse Link header for next/previous page URLs
    if "Link" in headers:
        link_header = headers["Link"]
        # Parse Link header format: <url>; rel='relation', <url>; rel='relation'
        # Example: </path?page=2>; rel='next', </path?page=1>; rel='previous'
        link_pattern = r'<([^>]+)>;\s*rel=[\'"]?(\w+)[\'"]?'
        matches = re.findall(link_pattern, link_header)

        for url, rel in matches:
            if rel == "next":
                pagination.next_page_url = url
            elif rel == "previous":
                pagination.previous_page_url = url

    return pagination
