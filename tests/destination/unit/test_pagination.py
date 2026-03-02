"""Unit tests for pagination utilities."""

import pytest
from unittest.mock import MagicMock
from requests import Response

from cloud_sdk_python.destination.utils._pagination import (
    PaginationInfo,
    PagedResult,
    parse_pagination_headers,
)


class TestPaginationInfo:
    """Tests for PaginationInfo dataclass."""

    def test_pagination_info_initialization(self):
        """Test creating PaginationInfo with all fields."""
        info = PaginationInfo(
            page_count=5,
            entity_count=47,
            next_page_url="/subaccountDestinations?$page=3&$pageSize=10",
            previous_page_url="/subaccountDestinations?$page=1&$pageSize=10"
        )

        assert info.page_count == 5
        assert info.entity_count == 47
        assert info.next_page_url == "/subaccountDestinations?$page=3&$pageSize=10"
        assert info.previous_page_url == "/subaccountDestinations?$page=1&$pageSize=10"

    def test_pagination_info_default_values(self):
        """Test PaginationInfo with default (None) values."""
        info = PaginationInfo()

        assert info.page_count is None
        assert info.entity_count is None
        assert info.next_page_url is None
        assert info.previous_page_url is None


class TestPagedResult:
    """Tests for PagedResult dataclass."""

    def test_paged_result_with_pagination(self):
        """Test creating PagedResult with pagination info."""
        items = [{"name": "dest1"}, {"name": "dest2"}]
        pagination = PaginationInfo(page_count=5, entity_count=47)

        result = PagedResult(items=items, pagination=pagination)

        assert result.items == items
        assert result.pagination == pagination
        assert result.pagination.page_count == 5
        assert result.pagination.entity_count == 47

    def test_paged_result_without_pagination(self):
        """Test creating PagedResult without pagination info."""
        items = [{"name": "dest1"}, {"name": "dest2"}]

        result = PagedResult(items=items)

        assert result.items == items
        assert result.pagination is None

    def test_paged_result_empty_items(self):
        """Test PagedResult with empty items list."""
        result = PagedResult(items=[], pagination=PaginationInfo(page_count=0, entity_count=0))

        assert result.items == []
        assert result.pagination.page_count == 0
        assert result.pagination.entity_count == 0


class TestParsePaginationHeaders:
    """Tests for parse_pagination_headers function."""

    def test_parse_pagination_headers_all_present(self):
        """Test parsing all pagination headers."""
        response = MagicMock(spec=Response)
        response.headers = {
            'Page-Count': '5',
            'Entity-Count': '47',
            'Link': '</subaccountDestinations?$page=1&$pageSize=10>; rel="previous", </subaccountDestinations?$page=3&$pageSize=10>; rel="next"'
        }

        result = parse_pagination_headers(response)

        assert result is not None
        assert result.page_count == 5
        assert result.entity_count == 47
        assert result.previous_page_url == '/subaccountDestinations?$page=1&$pageSize=10'
        assert result.next_page_url == '/subaccountDestinations?$page=3&$pageSize=10'

    def test_parse_pagination_headers_no_pagination(self):
        """Test parsing response without pagination headers."""
        response = MagicMock(spec=Response)
        response.headers = {
            'Content-Type': 'application/json',
            'Content-Length': '1234'
        }

        result = parse_pagination_headers(response)

        assert result is None

    def test_parse_pagination_headers_only_page_count(self):
        """Test parsing with only Page-Count header."""
        response = MagicMock(spec=Response)
        response.headers = {
            'Page-Count': '10'
        }

        result = parse_pagination_headers(response)

        assert result is not None
        assert result.page_count == 10
        assert result.entity_count is None
        assert result.next_page_url is None
        assert result.previous_page_url is None

    def test_parse_pagination_headers_only_entity_count(self):
        """Test parsing with only Entity-Count header."""
        response = MagicMock(spec=Response)
        response.headers = {
            'Entity-Count': '100'
        }

        result = parse_pagination_headers(response)

        assert result is not None
        assert result.page_count is None
        assert result.entity_count == 100
        assert result.next_page_url is None
        assert result.previous_page_url is None

    def test_parse_pagination_headers_only_link(self):
        """Test parsing with only Link header."""
        response = MagicMock(spec=Response)
        response.headers = {
            'Link': '</path?page=2>; rel="next"'
        }

        result = parse_pagination_headers(response)

        assert result is not None
        assert result.page_count is None
        assert result.entity_count is None
        assert result.next_page_url == '/path?page=2'
        assert result.previous_page_url is None

    def test_parse_pagination_headers_invalid_page_count(self):
        """Test parsing with invalid Page-Count value."""
        response = MagicMock(spec=Response)
        response.headers = {
            'Page-Count': 'invalid',
            'Entity-Count': '50'
        }

        result = parse_pagination_headers(response)

        assert result is not None
        assert result.page_count is None  # Should be None due to parsing error
        assert result.entity_count == 50

    def test_parse_pagination_headers_invalid_entity_count(self):
        """Test parsing with invalid Entity-Count value."""
        response = MagicMock(spec=Response)
        response.headers = {
            'Page-Count': '5',
            'Entity-Count': 'not-a-number'
        }

        result = parse_pagination_headers(response)

        assert result is not None
        assert result.page_count == 5
        assert result.entity_count is None  # Should be None due to parsing error

    def test_parse_pagination_headers_link_with_single_quotes(self):
        """Test parsing Link header with single quotes around rel."""
        response = MagicMock(spec=Response)
        response.headers = {
            'Link': "</path?page=2>; rel='next', </path?page=1>; rel='previous'"
        }

        result = parse_pagination_headers(response)

        assert result is not None
        assert result.next_page_url == '/path?page=2'
        assert result.previous_page_url == '/path?page=1'

    def test_parse_pagination_headers_link_without_quotes(self):
        """Test parsing Link header without quotes around rel."""
        response = MagicMock(spec=Response)
        response.headers = {
            'Link': '</path?page=2>; rel=next'
        }

        result = parse_pagination_headers(response)

        assert result is not None
        assert result.next_page_url == '/path?page=2'

    def test_parse_pagination_headers_link_multiple_rels(self):
        """Test parsing Link header with multiple rel values."""
        response = MagicMock(spec=Response)
        response.headers = {
            'Link': '</page1>; rel="first", </page2>; rel="previous", </page4>; rel="next", </page10>; rel="last"'
        }

        result = parse_pagination_headers(response)

        assert result is not None
        # Only next and previous should be captured
        assert result.next_page_url == '/page4'
        assert result.previous_page_url == '/page2'

    def test_parse_pagination_headers_link_with_complex_url(self):
        """Test parsing Link header with complex URL containing multiple parameters."""
        response = MagicMock(spec=Response)
        response.headers = {
            'Link': '</subaccountDestinations?$page=2&$pageSize=50&$pageCount=true&$entityCount=true>; rel="next"'
        }

        result = parse_pagination_headers(response)

        assert result is not None
        assert result.next_page_url == '/subaccountDestinations?$page=2&$pageSize=50&$pageCount=true&$entityCount=true'

    def test_parse_pagination_headers_empty_link(self):
        """Test parsing with empty Link header."""
        response = MagicMock(spec=Response)
        response.headers = {
            'Link': '',
            'Page-Count': '5'
        }

        result = parse_pagination_headers(response)

        assert result is not None
        assert result.page_count == 5
        assert result.next_page_url is None
        assert result.previous_page_url is None

    def test_parse_pagination_headers_malformed_link(self):
        """Test parsing with malformed Link header."""
        response = MagicMock(spec=Response)
        response.headers = {
            'Link': 'this is not a valid link header',
            'Page-Count': '3'
        }

        result = parse_pagination_headers(response)

        assert result is not None
        assert result.page_count == 3
        # Should gracefully handle malformed link and not set URLs
        assert result.next_page_url is None
        assert result.previous_page_url is None
