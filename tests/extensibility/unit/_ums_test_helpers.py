"""Shared fixtures and test data for UMS transport tests."""

import base64
import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from sap_cloud_sdk.extensibility._ums_transport import (
    UmsTransport,
    ENV_CONHOS_LANDSCAPE,
)
from sap_cloud_sdk.extensibility.config import ExtensibilityConfig


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AGENT_ORD_ID = "sap.ai:agent:employeeOnboarding:v1"

# Fake PEM certificate content for testing
_FAKE_PEM = b"-----BEGIN CERTIFICATE-----\nfakecertdata\n-----END CERTIFICATE-----\n"
_FAKE_PEM_B64 = base64.b64encode(_FAKE_PEM).decode()


# ---------------------------------------------------------------------------
# UMS response fixtures
# ---------------------------------------------------------------------------

UMS_RESPONSE_SINGLE = {
    "data": {
        "EXTHUB__ExtCapImplementationInstances": {
            "edges": [
                {
                    "node": {
                        "id": "ext-instance-1",
                        "title": "ServiceNow Extension",
                        "extensionVersion": "2.1.0",
                        "capabilityImplementations": [
                            {
                                "capabilityId": "default",
                                "instruction": {
                                    "text": "Use ServiceNow tools for ticket management."
                                },
                                "tools": {
                                    "additions": [
                                        {
                                            "type": "MCP",
                                            "mcpConfig": {
                                                "globalTenantId": "tenant-sn-1",
                                                "ordId": "sap.mcp:apiResource:serviceNow:v1",
                                                "toolNames": [
                                                    "create_ticket",
                                                    "update_ticket",
                                                ],
                                            },
                                        }
                                    ]
                                },
                                "hooks": [
                                    {
                                        "id": "9f6e5f66-7e4f-4ef0-a9f6-e6e1c1220c11",
                                        "hookId": "before_tool_execution",
                                        "type": "BEFORE",
                                        "name": "Before Tool Execution",
                                        "onFailure": "CONTINUE",
                                        "timeout": 30,
                                        "deploymentType": "N8N",
                                        "canShortCircuit": False,
                                        "n8nWorkflowConfig": {
                                            "workflowId": "wf-before-001",
                                            "method": "POST",
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                }
            ],
            "pageInfo": {"hasNextPage": False, "cursor": None},
        }
    }
}

UMS_RESPONSE_MULTIPLE = {
    "data": {
        "EXTHUB__ExtCapImplementationInstances": {
            "edges": [
                {
                    "node": {
                        "id": "ext-instance-1",
                        "title": "ServiceNow Extension",
                        "extensionVersion": "1.0.0",
                        "capabilityImplementations": [
                            {
                                "capabilityId": "default",
                                "instruction": {"text": "ServiceNow instruction."},
                                "tools": {
                                    "additions": [
                                        {
                                            "type": "MCP",
                                            "mcpConfig": {
                                                "globalTenantId": "tenant-sn-2",
                                                "ordId": "sap.mcp:apiResource:serviceNow:v1",
                                                "toolNames": ["create_ticket"],
                                            },
                                        }
                                    ]
                                },
                                "hooks": [],
                            }
                        ],
                    }
                },
                {
                    "node": {
                        "id": "ext-instance-2",
                        "title": "Jira Extension",
                        "extensionVersion": "3.2.1",
                        "capabilityImplementations": [
                            {
                                "capabilityId": "default",
                                "instruction": {"text": "Jira instruction."},
                                "tools": {
                                    "additions": [
                                        {
                                            "type": "MCP",
                                            "mcpConfig": {
                                                "globalTenantId": "tenant-jira-1",
                                                "ordId": "sap.mcp:apiResource:jira:v1",
                                                "toolNames": ["create_issue"],
                                            },
                                        }
                                    ]
                                },
                                "hooks": [
                                    {
                                        "id": "6a9e0cef-eed6-4f1b-9f86-3d8e9f5c1d22",
                                        "hookId": "after_tool_execution",
                                        "type": "AFTER",
                                        "name": "After Tool Execution",
                                        "onFailure": "CONTINUE",
                                        "timeout": 30,
                                        "deploymentType": "N8N",
                                        "canShortCircuit": False,
                                        "n8nWorkflowConfig": {
                                            "workflowId": "wf-after-001",
                                            "method": "POST",
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                },
            ],
            "pageInfo": {"hasNextPage": False, "cursor": None},
        }
    }
}

UMS_RESPONSE_EMPTY = {
    "data": {
        "EXTHUB__ExtCapImplementationInstances": {
            "edges": [],
            "pageInfo": {"hasNextPage": False, "cursor": None},
        }
    }
}

UMS_RESPONSE_NO_INSTRUCTION = {
    "data": {
        "EXTHUB__ExtCapImplementationInstances": {
            "edges": [
                {
                    "node": {
                        "id": "ext-1",
                        "title": "Minimal Extension",
                        "extensionVersion": "0.1.0",
                        "capabilityImplementations": [
                            {
                                "capabilityId": "default",
                                "tools": {
                                    "additions": [
                                        {
                                            "type": "MCP",
                                            "mcpConfig": {
                                                "globalTenantId": "tenant-min-1",
                                                "ordId": "sap.mcp:apiResource:minimal:v1",
                                                "toolNames": ["do_thing"],
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
            "pageInfo": {"hasNextPage": False, "cursor": None},
        }
    }
}

UMS_RESPONSE_EMPTY_INSTRUCTION = {
    "data": {
        "EXTHUB__ExtCapImplementationInstances": {
            "edges": [
                {
                    "node": {
                        "id": "ext-1",
                        "title": "Empty Instruction Extension",
                        "extensionVersion": "1.0.0",
                        "capabilityImplementations": [
                            {
                                "capabilityId": "default",
                                "instruction": {"text": ""},
                                "tools": {"additions": []},
                                "hooks": [],
                            }
                        ],
                    }
                }
            ],
            "pageInfo": {"hasNextPage": False, "cursor": None},
        }
    }
}

UMS_RESPONSE_DIFFERENT_CAPABILITY = {
    "data": {
        "EXTHUB__ExtCapImplementationInstances": {
            "edges": [
                {
                    "node": {
                        "id": "ext-1",
                        "title": "Other Extension",
                        "extensionVersion": "2.0.0",
                        "capabilityImplementations": [
                            {
                                "capabilityId": "onboarding",
                                "instruction": {"text": "Onboarding instruction."},
                                "tools": {
                                    "additions": [
                                        {
                                            "type": "MCP",
                                            "mcpConfig": {
                                                "globalTenantId": "tenant-onb-1",
                                                "ordId": "sap.mcp:apiResource:onboarding:v1",
                                                "toolNames": ["onboard_user"],
                                            },
                                        }
                                    ]
                                },
                                "hooks": [],
                            },
                            {
                                "capabilityId": "default",
                                "instruction": {"text": "Default instruction."},
                                "tools": {
                                    "additions": [
                                        {
                                            "type": "MCP",
                                            "mcpConfig": {
                                                "globalTenantId": "tenant-gen-1",
                                                "ordId": "sap.mcp:apiResource:general:v1",
                                                "toolNames": ["general_tool"],
                                            },
                                        }
                                    ]
                                },
                                "hooks": [],
                            },
                        ],
                    }
                }
            ],
            "pageInfo": {"hasNextPage": False, "cursor": None},
        }
    }
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _make_config(**overrides):
    defaults: dict = {
        "destination_name": None,
        "destination_instance": "default",
    }
    defaults.update(overrides)
    return ExtensibilityConfig(**defaults)


def _make_dest(url="https://ums.example.com", cert_content=_FAKE_PEM_B64):
    dest = MagicMock()
    dest.url = url
    if cert_content is not None:
        cert = MagicMock()
        cert.name = "client-cert.pem"
        cert.content = cert_content
        cert.type = "PEM"
        dest.certificates = [cert]
    else:
        dest.certificates = []
    return dest


def _make_httpx_response(json_body, status_code=200):
    """Create a mock httpx.Response with the given body."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.json.return_value = json_body
    response.text = json.dumps(json_body)
    response.raise_for_status = MagicMock()
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}",
            request=MagicMock(),
            response=response,
        )
    return response


def _make_transport(monkeypatch, dest=None):
    """Create a UmsTransport with mocked destination client."""
    monkeypatch.setenv(ENV_CONHOS_LANDSCAPE, "exttest-dev-eu12")
    with patch(
        "sap_cloud_sdk.extensibility._ums_transport.create_destination_client"
    ) as mock_dest_client:
        config = _make_config()
        if dest is None:
            dest = _make_dest()
        mock_dest_client.return_value.get_destination.return_value = dest
        transport = UmsTransport(AGENT_ORD_ID, config)
        return transport, mock_dest_client.return_value
