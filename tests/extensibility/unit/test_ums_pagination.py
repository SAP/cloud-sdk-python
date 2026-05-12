"""Tests for UMS transport cursor-based pagination."""

from unittest.mock import MagicMock, patch

import pytest

from sap_cloud_sdk.extensibility._ums_transport import (
    UmsTransport,
    _MAX_PAGES,
    ENV_CONHOS_LANDSCAPE,
)
from sap_cloud_sdk.extensibility.exceptions import TransportError

from tests.extensibility.unit._ums_test_helpers import (
    AGENT_ORD_ID,
    UMS_RESPONSE_SINGLE,
    UMS_RESPONSE_EMPTY,
    _make_config,
    _make_dest,
    _make_httpx_response,
)


class TestUmsTransportPagination:
    """Tests for cursor-based pagination across multiple GraphQL pages."""

    @pytest.fixture(autouse=True)
    def _set_landscape_env(self, monkeypatch):
        monkeypatch.setenv(ENV_CONHOS_LANDSCAPE, "exttest-dev-eu12")

    @patch("sap_cloud_sdk.extensibility._ums_transport.create_destination_client")
    def _make_transport(self, mock_dest_client, dest=None):
        config = _make_config()
        if dest is None:
            dest = _make_dest()
        mock_dest_client.return_value.get_destination.return_value = dest
        transport = UmsTransport(AGENT_ORD_ID, config)
        return transport, mock_dest_client.return_value

    def test_single_page_no_next(self):
        """A response with hasNextPage=False results in one HTTP call."""
        transport, _ = self._make_transport()
        response = _make_httpx_response(UMS_RESPONSE_SINGLE)

        with patch(
            "sap_cloud_sdk.extensibility._ums_transport.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = response

            result = transport.get_extension_capability_implementation()

        assert mock_client.post.call_count == 1
        assert result.extension_names == ["ServiceNow Extension"]
        assert len(result.mcp_servers) == 1

    def test_multiple_pages_accumulates_edges(self):
        """When hasNextPage=True, transport fetches additional pages and merges edges."""
        transport, _ = self._make_transport()

        page1_response = _make_httpx_response(
            {
                "data": {
                    "EXTHUB__ExtCapImplementationInstances": {
                        "edges": [
                            {
                                "node": {
                                    "id": "ext-1",
                                    "title": "Extension A",
                                    "extensionVersion": "1.0.0",
                                    "capabilityImplementations": [
                                        {
                                            "capabilityId": "default",
                                            "instruction": {"text": "A instruction."},
                                            "tools": {
                                                "additions": [
                                                    {
                                                        "type": "MCP",
                                                        "mcpConfig": {
                                                            "globalTenantId": "tenant-a-1",
                                                            "ordId": "sap.mcp:a:v1",
                                                            "toolNames": ["tool_a"],
                                                        },
                                                    }
                                                ]
                                            },
                                            "hooks": [],
                                        }
                                    ],
                                }
                            }
                        ],
                        "pageInfo": {"hasNextPage": True, "cursor": "cursor-page-1"},
                    }
                }
            }
        )

        page2_response = _make_httpx_response(
            {
                "data": {
                    "EXTHUB__ExtCapImplementationInstances": {
                        "edges": [
                            {
                                "node": {
                                    "id": "ext-2",
                                    "title": "Extension B",
                                    "extensionVersion": "2.0.0",
                                    "capabilityImplementations": [
                                        {
                                            "capabilityId": "default",
                                            "instruction": {"text": "B instruction."},
                                            "tools": {
                                                "additions": [
                                                    {
                                                        "type": "MCP",
                                                        "mcpConfig": {
                                                            "globalTenantId": "tenant-b-1",
                                                            "ordId": "sap.mcp:b:v1",
                                                            "toolNames": ["tool_b"],
                                                        },
                                                    }
                                                ]
                                            },
                                            "hooks": [],
                                        }
                                    ],
                                }
                            }
                        ],
                        "pageInfo": {"hasNextPage": False, "cursor": "cursor-page-2"},
                    }
                }
            }
        )

        with patch(
            "sap_cloud_sdk.extensibility._ums_transport.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = [page1_response, page2_response]

            result = transport.get_extension_capability_implementation()

        # Two HTTP calls
        assert mock_client.post.call_count == 2

        # Both extensions are merged
        assert result.extension_names == ["Extension A", "Extension B"]
        assert len(result.mcp_servers) == 2
        assert result.mcp_servers[0].ord_id == "sap.mcp:a:v1"
        assert result.mcp_servers[1].ord_id == "sap.mcp:b:v1"

        # Source mapping includes both extensions with their versions
        assert result.source is not None
        assert result.source.tools["tool_a"].extension_version == "1.0.0"
        assert result.source.tools["tool_b"].extension_version == "2.0.0"

        # Instructions from all extensions are joined
        assert result.instruction == "A instruction.\n\nB instruction."

    def test_cursor_sent_on_subsequent_pages(self):
        """The cursor from pageInfo is passed as the 'after' variable on the next request."""
        transport, _ = self._make_transport()

        page1_response = _make_httpx_response(
            {
                "data": {
                    "EXTHUB__ExtCapImplementationInstances": {
                        "edges": [
                            {
                                "node": {
                                    "id": "ext-1",
                                    "title": "Ext",
                                    "extensionVersion": "1.0.0",
                                    "capabilityImplementations": [
                                        {
                                            "capabilityId": "default",
                                            "tools": {"additions": []},
                                            "hooks": [],
                                        }
                                    ],
                                }
                            }
                        ],
                        "pageInfo": {"hasNextPage": True, "cursor": "abc123"},
                    }
                }
            }
        )
        page2_response = _make_httpx_response(
            {
                "data": {
                    "EXTHUB__ExtCapImplementationInstances": {
                        "edges": [],
                        "pageInfo": {"hasNextPage": False, "cursor": None},
                    }
                }
            }
        )

        # Capture snapshots of the variables dict at each call
        captured_vars = []

        with patch(
            "sap_cloud_sdk.extensibility._ums_transport.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = [page1_response, page2_response]

            original_post = mock_client.post

            def capturing_post(*args, **kwargs):
                # Snapshot the variables before they can be mutated
                body = kwargs.get("json", {})
                captured_vars.append(dict(body.get("variables", {})))
                return original_post(*args, **kwargs)

            mock_client.post = MagicMock(side_effect=capturing_post)

            transport.get_extension_capability_implementation()

        assert len(captured_vars) == 2

        # First call: no 'after' variable (uses _GRAPHQL_QUERY without $after)
        assert "after" not in captured_vars[0]

        # Second call: after="abc123" (uses _GRAPHQL_QUERY_WITH_CURSOR)
        assert captured_vars[1]["after"] == "abc123"

    def test_empty_first_page_no_further_requests(self):
        """Empty edges with hasNextPage=False stops after one request."""
        transport, _ = self._make_transport()
        response = _make_httpx_response(UMS_RESPONSE_EMPTY)

        with patch(
            "sap_cloud_sdk.extensibility._ums_transport.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = response

            result = transport.get_extension_capability_implementation()

        assert mock_client.post.call_count == 1
        assert result.extension_names == []
        assert result.mcp_servers == []

    def test_error_on_second_page_raises(self):
        """If the second page returns an error, TransportError is raised."""
        transport, _ = self._make_transport()

        page1_response = _make_httpx_response(
            {
                "data": {
                    "EXTHUB__ExtCapImplementationInstances": {
                        "edges": [
                            {
                                "node": {
                                    "id": "ext-1",
                                    "title": "Ext",
                                    "extensionVersion": "1.0.0",
                                    "capabilityImplementations": [
                                        {
                                            "capabilityId": "default",
                                            "tools": {"additions": []},
                                            "hooks": [],
                                        }
                                    ],
                                }
                            }
                        ],
                        "pageInfo": {"hasNextPage": True, "cursor": "page1-cursor"},
                    }
                }
            }
        )
        page2_error = _make_httpx_response({"error": "server error"}, status_code=500)

        with patch(
            "sap_cloud_sdk.extensibility._ums_transport.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = [page1_response, page2_error]

            with pytest.raises(TransportError, match="UMS returned HTTP 500"):
                transport.get_extension_capability_implementation()

    def test_missing_page_info_stops_pagination(self):
        """If pageInfo is absent, treat as no next page (don't loop forever)."""
        transport, _ = self._make_transport()

        response = _make_httpx_response(
            {
                "data": {
                    "EXTHUB__ExtCapImplementationInstances": {
                        "edges": [
                            {
                                "node": {
                                    "id": "ext-1",
                                    "title": "Ext",
                                    "extensionVersion": "1.0.0",
                                    "capabilityImplementations": [
                                        {
                                            "capabilityId": "default",
                                            "tools": {"additions": []},
                                            "hooks": [],
                                        }
                                    ],
                                }
                            }
                        ],
                    }
                }
            }
        )

        with patch(
            "sap_cloud_sdk.extensibility._ums_transport.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = response

            result = transport.get_extension_capability_implementation()

        assert mock_client.post.call_count == 1
        assert result.extension_names == ["Ext"]

    def test_max_pages_constant(self):
        """Safety limit constant is 100."""
        assert _MAX_PAGES == 100

