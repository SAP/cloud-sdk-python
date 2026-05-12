"""Tests for ORD integration helpers."""

from unittest.mock import MagicMock


from sap_cloud_sdk.extensibility._ord_integration import (
    _derive_mcp_name_from_ord_id,
    _map_capability_to_integration_dependencies,
    add_extension_integration_dependencies,
)
from sap_cloud_sdk.extensibility._models import (
    ExtensionCapabilityImplementation,
    McpServer,
)


class TestDeriveMcpNameFromOrdId:
    """Tests for _derive_mcp_name_from_ord_id."""

    def test_sap_s4_namespace(self):
        assert (
            _derive_mcp_name_from_ord_id("sap.s4:apiResource:s4bpintelmcp:v1") == "S4"
        )

    def test_sap_ariba_namespace(self):
        assert (
            _derive_mcp_name_from_ord_id("sap.ariba:apiResource:hardwareMcp:v1")
            == "Ariba"
        )

    def test_simple_namespace(self):
        assert (
            _derive_mcp_name_from_ord_id("sap.mcp:apiResource:serviceNow:v1") == "Mcp"
        )

    def test_multiple_dots_namespace(self):
        assert (
            _derive_mcp_name_from_ord_id(
                "sap.btpn8n:apiResource:ManagedN8nMcpServer:v1"
            )
            == "Btpn8N"
        )

    def test_preserves_full_namespace(self):
        result = _derive_mcp_name_from_ord_id("sap.custom:apiResource:customMcp:v1")
        assert result == "Custom"


class TestMapCapabilityToIntegrationDependencies:
    """Tests for _map_capability_to_integration_dependencies."""

    def test_no_mcp_servers_returns_empty(self):
        capability_impl = ExtensionCapabilityImplementation(
            capability_id="default",
            mcp_servers=[],
        )
        result = _map_capability_to_integration_dependencies(capability_impl)
        assert result == []

    def test_with_mcp_servers_no_base_deps(self):
        capability_impl = ExtensionCapabilityImplementation(
            capability_id="default",
            mcp_servers=[
                McpServer(
                    ord_id="sap.s4:apiResource:s4bpintelmcp:v1",
                    global_tenant_id="tenant-s4-1",
                ),
            ],
        )
        agent = {
            "ordId": "sap.agtpocext:agent:extensibility-agent:v1",
            "partOfPackage": "sap.agtpocext:package:test:v1",
        }

        result = _map_capability_to_integration_dependencies(
            capability_impl, agent=agent
        )

        assert len(result) == 1
        dep = result[0]
        assert dep["ordId"] == "sap.agtpocext:integrationDependency:extension-mcp:v1"
        assert dep["title"] == "Extension MCP Servers"
        assert dep["version"] == "1.0.0"
        assert dep["releaseStatus"] == "active"
        assert dep["visibility"] == "public"
        assert dep["mandatory"] is False
        assert dep["partOfPackage"] == "sap.agtpocext:package:test:v1"
        assert "lastUpdate" in dep
        assert len(dep["aspects"]) == 1
        assert dep["aspects"][0]["title"] == "S4 Extension MCP"
        assert dep["aspects"][0]["mandatory"] is False
        assert (
            dep["aspects"][0]["apiResources"][0]["ordId"]
            == "sap.s4:apiResource:s4bpintelmcp:v1"
        )

    def test_with_duplicate_mcps_filtered(self):
        """MCP servers already in base are filtered out."""
        capability_impl = ExtensionCapabilityImplementation(
            capability_id="default",
            mcp_servers=[
                McpServer(
                    ord_id="sap.s4:apiResource:s4bpintelmcp:v1",
                    global_tenant_id="tenant-s4-1",
                ),
                McpServer(
                    ord_id="sap.btpn8n:apiResource:ManagedN8nMcpServer:v1",
                    global_tenant_id="tenant-n8n-1",
                ),
            ],
        )
        agent = {
            "ordId": "sap.agtpocext:agent:extensibility-agent:v1",
            "partOfPackage": "sap.agtpocext:package:test:v1",
        }

        base_integration_deps = [
            {
                "ordId": "sap.agtpocext:integrationDependency:n8n-mcp:v1",
                "aspects": [
                    {
                        "title": "N8n MCP",
                        "apiResources": [
                            {"ordId": "sap.btpn8n:apiResource:ManagedN8nMcpServer:v1"}
                        ],
                    }
                ],
            }
        ]

        result = _map_capability_to_integration_dependencies(
            capability_impl, agent=agent, base_integration_deps=base_integration_deps
        )

        assert len(result) == 1
        dep = result[0]
        assert len(dep["aspects"]) == 1
        assert (
            dep["aspects"][0]["apiResources"][0]["ordId"]
            == "sap.s4:apiResource:s4bpintelmcp:v1"
        )

    def test_all_mcps_duplicate_returns_empty(self):
        """All MCP servers are duplicates, returns empty list."""
        capability_impl = ExtensionCapabilityImplementation(
            capability_id="default",
            mcp_servers=[
                McpServer(
                    ord_id="sap.btpn8n:apiResource:ManagedN8nMcpServer:v1",
                    global_tenant_id="tenant-n8n-1",
                ),
            ],
        )
        agent = {
            "ordId": "sap.agtpocext:agent:extensibility-agent:v1",
            "partOfPackage": "sap.agtpocext:package:test:v1",
        }

        base_integration_deps = [
            {
                "ordId": "sap.agtpocext:integrationDependency:n8n-mcp:v1",
                "aspects": [
                    {
                        "title": "N8n MCP",
                        "apiResources": [
                            {"ordId": "sap.btpn8n:apiResource:ManagedN8nMcpServer:v1"}
                        ],
                    }
                ],
            }
        ]

        result = _map_capability_to_integration_dependencies(
            capability_impl, agent=agent, base_integration_deps=base_integration_deps
        )

        assert result == []

    def test_multiple_mcps_all_new(self):
        """Multiple new MCP servers, none duplicating base."""
        capability_impl = ExtensionCapabilityImplementation(
            capability_id="default",
            mcp_servers=[
                McpServer(
                    ord_id="sap.s4:apiResource:s4bpintelmcp:v1",
                    global_tenant_id="tenant-s4-1",
                ),
                McpServer(
                    ord_id="sap.ariba:apiResource:hardwareMcp:v1",
                    global_tenant_id="tenant-ariba-1",
                ),
            ],
        )
        agent = {
            "ordId": "sap.agtpocext:agent:extensibility-agent:v1",
            "partOfPackage": "sap.agtpocext:package:test:v1",
        }

        result = _map_capability_to_integration_dependencies(
            capability_impl, agent=agent
        )

        assert len(result) == 1
        dep = result[0]
        assert len(dep["aspects"]) == 2
        aspect_titles = [a["title"] for a in dep["aspects"]]
        assert "S4 Extension MCP" in aspect_titles
        assert "Ariba Extension MCP" in aspect_titles


class TestAddExtensionIntegrationDependencies:
    """Tests for add_extension_integration_dependencies."""

    def test_no_ext_client_returns_early(self):
        """When ext_client is None, returns early without modifying document."""
        document = {
            "agents": [{"ordId": "sap.agtpocext:agent:extensibility-agent:v1"}],
            "integrationDependencies": [],
        }

        add_extension_integration_dependencies(document=document, ext_client=None)

        assert document["integrationDependencies"] == []

    def test_with_ext_client_adds_integration_deps(self):
        """With ext_client, adds integration dependencies to document."""
        mock_client = MagicMock()
        mock_client.get_extension_capability_implementation.return_value = (
            ExtensionCapabilityImplementation(
                capability_id="default",
                mcp_servers=[
                    McpServer(
                        ord_id="sap.s4:apiResource:s4bpintelmcp:v1",
                        global_tenant_id="tenant-s4-1",
                    ),
                ],
            )
        )

        document = {
            "agents": [
                {
                    "ordId": "sap.agtpocext:agent:extensibility-agent:v1",
                    "partOfPackage": "sap.agtpocext:package:test:v1",
                    "integrationDependencies": [],
                }
            ],
            "integrationDependencies": [],
        }

        add_extension_integration_dependencies(
            document=document,
            local_tenant_id="tenant-1",
            ext_client=mock_client,
        )

        assert len(document["integrationDependencies"]) == 1
        dep = document["integrationDependencies"][0]
        assert dep["ordId"] == "sap.agtpocext:integrationDependency:extension-mcp:v1"
        assert len(dep["aspects"]) == 1

        agent = document["agents"][0]
        assert (
            "sap.agtpocext:integrationDependency:extension-mcp:v1"
            in agent["integrationDependencies"]
        )

    def test_existing_base_integration_deps_preserved(self):
        """Existing base integration dependencies are preserved."""
        mock_client = MagicMock()
        mock_client.get_extension_capability_implementation.return_value = (
            ExtensionCapabilityImplementation(
                capability_id="default",
                mcp_servers=[
                    McpServer(
                        ord_id="sap.s4:apiResource:s4bpintelmcp:v1",
                        global_tenant_id="tenant-s4-1",
                    ),
                ],
            )
        )

        document = {
            "agents": [
                {
                    "ordId": "sap.agtpocext:agent:extensibility-agent:v1",
                    "partOfPackage": "sap.agtpocext:package:test:v1",
                    "integrationDependencies": [],
                }
            ],
            "integrationDependencies": [
                {
                    "ordId": "sap.agtpocext:integrationDependency:n8n-mcp:v1",
                    "title": "N8N MCP Servers",
                    "aspects": [
                        {
                            "title": "N8n MCP",
                            "apiResources": [
                                {
                                    "ordId": "sap.btpn8n:apiResource:ManagedN8nMcpServer:v1"
                                }
                            ],
                        }
                    ],
                }
            ],
        }

        add_extension_integration_dependencies(
            document=document,
            local_tenant_id="tenant-1",
            ext_client=mock_client,
        )

        ord_ids = [dep["ordId"] for dep in document["integrationDependencies"]]
        assert "sap.agtpocext:integrationDependency:n8n-mcp:v1" in ord_ids
        assert "sap.agtpocext:integrationDependency:extension-mcp:v1" in ord_ids

    def test_empty_capability_returns_early(self):
        """When no MCP servers returned, returns early without adding."""
        mock_client = MagicMock()
        mock_client.get_extension_capability_implementation.return_value = (
            ExtensionCapabilityImplementation(
                capability_id="default",
                mcp_servers=[],
            )
        )

        document = {
            "agents": [{"ordId": "sap.agtpocext:agent:extensibility-agent:v1"}],
            "integrationDependencies": [],
        }

        add_extension_integration_dependencies(
            document=document,
            local_tenant_id="tenant-1",
            ext_client=mock_client,
        )

        assert document["integrationDependencies"] == []
