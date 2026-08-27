"""Low-level HTTP helper for the Agent Memory service."""

from __future__ import annotations

import logging
from typing import Any, Optional
from urllib.parse import quote, urlencode

from requests.exceptions import RequestException, Timeout

from sap_cloud_sdk.agent_memory.exceptions import (
    AgentMemoryHttpError,
    AgentMemoryNotFoundError,
)
from sap_cloud_sdk.core._http_client import HttpClient, HttpMethod

logger = logging.getLogger(__name__)


def _request(
    http: HttpClient,
    method: HttpMethod,
    path: str,
    *,
    params: Optional[dict[str, Any]] = None,
    tenant_subdomain: Optional[str] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Execute an Agent Memory HTTP request and map errors to domain exceptions."""
    logger.debug("%s %s (tenant=%r)", method.value, path, tenant_subdomain)

    if params:
        path = f"{path}?{urlencode(params, quote_via=quote)}"

    try:
        response = http.request(
            method,
            path,
            tenant_subdomain=tenant_subdomain,
            headers={"Content-Type": "application/json"},
            **kwargs,
        )
    except Timeout as exc:
        raise AgentMemoryHttpError(f"Request timed out: {method.value} {path}") from exc
    except RequestException as exc:
        raise AgentMemoryHttpError(f"Request failed: {method.value} {path} — {exc}") from exc
    except Exception as exc:
        raise AgentMemoryHttpError(str(exc)) from exc

    if response.status_code == 204 or not response.content:
        return {}

    if response.status_code == 404:
        raise AgentMemoryNotFoundError(
            f"Resource not found: {method.value} {path}",
            status_code=404,
            response_text=response.text,
        )

    if not response.ok:
        raise AgentMemoryHttpError(
            f"Agent Memory service request failed. "
            f"Method: {method.value}, Path: {path}, "
            f"Status: {response.status_code}, Response: {response.text}",
            status_code=response.status_code,
            response_text=response.text,
        )

    return response.json()
