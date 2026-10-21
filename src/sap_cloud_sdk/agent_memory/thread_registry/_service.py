"""Service-backed thread registry using the Agent Memory Service REST API."""

from __future__ import annotations

import json as _json
import logging
from typing import Any, Optional
from urllib.parse import quote

from requests.exceptions import RequestException, Timeout

from sap_cloud_sdk.agent_memory.client import _require_ias_token
from sap_cloud_sdk.agent_memory.config import AgentMemoryConfig
from sap_cloud_sdk.agent_memory.exceptions import (
    AgentMemoryHttpError,
    AgentMemoryNotFoundError,
    AgentMemoryThreadNotFoundError,
    AgentMemoryValidationError,
)
from sap_cloud_sdk.agent_memory.thread_registry._base import (
    BaseThreadRegistry,
    ThreadPage,
    ThreadRegistryEntry,
    _raise_thread_conflict,
    _raise_thread_expired,
    _validate_ttl,
)
from sap_cloud_sdk.core.protocol.http import (
    HttpClient,
    HttpMethod,
    IasAuthProvider,
    XsuaaAuthProvider,
)
from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics

logger = logging.getLogger(__name__)

_THREAD_COLLECTION = "/v1/agent/threads"


# ---------------------------------------------------------------------------
# OData URL helpers
# ---------------------------------------------------------------------------


def _escape_odata_string(value: str) -> str:
    """Double single quotes for OData string literals."""
    return value.replace("'", "''")


def _odata_entity_path(thread_id: str) -> str:
    """Build OData entity-key path: /v1/agent/threads(threadId='...')."""
    encoded = quote(_escape_odata_string(thread_id), safe="")
    return f"{_THREAD_COLLECTION}(threadId='{encoded}')"


def _build_list_path(
    agent_id: Optional[str],
    invoker_id: Optional[str],
    limit: Optional[int],
    offset: int,
) -> str:
    """Build the GET path for list_threads, keeping OData $ params un-encoded."""
    filter_parts: list[str] = []
    if agent_id is not None:
        filter_parts.append(f"agentId eq '{_escape_odata_string(agent_id)}'")
    if invoker_id is not None:
        filter_parts.append(f"invokerId eq '{_escape_odata_string(invoker_id)}'")

    # Build OData query string manually — urlencode would encode $ as %24.
    parts = [
        f"$orderby={quote('updatedAt desc', safe=',')}",
        "$count=true",
    ]
    if limit is not None:
        parts.append(f"$top={limit}")
    if offset > 0:
        parts.append(f"$skip={offset}")
    if filter_parts:
        parts.append(f"$filter={quote(' and '.join(filter_parts))}")

    return f"{_THREAD_COLLECTION}?{'&'.join(parts)}"


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _is_expired_response(exc: AgentMemoryHttpError) -> bool:
    """Return True if a 409 response indicates an expired thread (vs. conflict).

    Tries structured JSON error codes first (``error.code``, ``errorCode``),
    then falls back to substring matching on the raw response body.  Two-layer
    detection means a service that upgrades from prose-only errors to
    machine-readable codes is handled automatically.
    """
    if exc.response_text:
        try:
            body = _json.loads(exc.response_text)
            # Check common SAP/OData structured error shapes.
            code: str = (
                (body.get("error") or {}).get("code", "")
                or body.get("errorCode", "")
                or body.get("code", "")
            )
            if code:
                return "expired" in code.lower()
            # No code field — fall through to string matching below.
        except (ValueError, TypeError):
            pass  # response body is not JSON
    # String-match fallback: search only the raw response body. The exception
    # message embeds method/path/status context that could contain "expired"
    # from an unrelated error (e.g. a 409 whose body says "OAuth token expired").
    return "expired" in (exc.response_text or "").lower()


def _parse_entry(row: dict[str, Any]) -> ThreadRegistryEntry:
    # The service always returns camelCase JSON (SAP CAP/OData convention).
    # Using plain .get() avoids the lossy `or` operator (which would discard
    # a legitimate empty-string value by falling through to the next key).
    return ThreadRegistryEntry(
        threadId=row.get("threadId", ""),
        agentId=row.get("agentId", ""),
        invokerId=row.get("invokerId", ""),
        description=row.get("description"),
        createdAt=row.get("createdAt"),
        updatedAt=row.get("updatedAt"),
        expiresAt=row.get("expiresAt"),
        threadTtl=row.get("threadTtl"),
        metadata=row.get("metadata"),
    )


# ---------------------------------------------------------------------------
# Registry implementation
# ---------------------------------------------------------------------------


class SAPAgentMemoryThreadRegistry(BaseThreadRegistry):
    """Service-backed thread registry for the SAP Agent Memory Service.

    Uses the SDK's :class:`~sap_cloud_sdk.core.protocol.http.HttpClient`
    for OAuth2 or IAS authentication and request execution. Instantiate via
    :func:`create_thread_registry` rather than directly.

    **Lifecycle**: the registry owns its :class:`~sap_cloud_sdk.core.protocol.http.HttpClient`
    (OAuth sessions, underlying ``requests.Session`` objects). Call :meth:`close` or use the
    registry as a context manager when you are done with it::

        with create_thread_registry() as reg:
            reg.create_or_register_thread(...)

    Args:
        config: Service configuration (base URL, OAuth2 credentials, timeout).
        default_ttl_seconds: Registry-level default sliding TTL in seconds.
            Applied when a per-call ``ttl_seconds`` is not supplied.
    """

    def __init__(
        self,
        config: AgentMemoryConfig,
        *,
        default_ttl_seconds: Optional[int] = None,
    ) -> None:
        _validate_ttl(default_ttl_seconds)
        is_ias = config.auth_mode == "ias"
        self._ias_mode = is_ias
        if is_ias:
            auth = IasAuthProvider()
        else:
            auth = XsuaaAuthProvider(lambda: config)
        self._http = HttpClient(config.base_url, auth, timeout=config.timeout)
        self._base_url = config.base_url.rstrip("/")
        self._default_ttl = default_ttl_seconds

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP transport and release OAuth sessions."""
        self._http.close()

    def __enter__(self) -> "SAPAgentMemoryThreadRegistry":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _ttl(self, ttl_seconds: Optional[int]) -> Optional[int]:
        return ttl_seconds if ttl_seconds is not None else self._default_ttl

    def _strip_base(self, url: str) -> str:
        """Strip the base URL prefix from an absolute URL, returning just the path."""
        if url.startswith(self._base_url):
            return url[len(self._base_url) :]
        return url

    def _request(
        self,
        method: HttpMethod,
        path: str,
        *,
        tenant_subdomain: Optional[str] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if self._ias_mode:
            _require_ias_token()
        try:
            response = self._http.request(
                method,
                path,
                tenant_subdomain=tenant_subdomain,
                headers={"Content-Type": "application/json"},
                **kwargs,
            )
        except Timeout as exc:
            raise AgentMemoryHttpError(
                f"Request timed out: {method.value} {path}"
            ) from exc
        except RequestException as exc:
            raise AgentMemoryHttpError(
                f"Request failed: {method.value} {path} — {exc}"
            ) from exc
        except AgentMemoryValidationError:
            raise
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
                f"Thread registry request failed. "
                f"Method: {method.value}, Path: {path}, "
                f"Status: {response.status_code}, Response: {response.text}",
                status_code=response.status_code,
                response_text=response.text,
            )
        return response.json()

    # ------------------------------------------------------------------
    # create_or_register_thread
    # ------------------------------------------------------------------

    @record_metrics(
        Module.AGENT_MEMORY, Operation.AGENT_MEMORY_CREATE_OR_REGISTER_THREAD
    )
    def create_or_register_thread(
        self,
        agent_id: str,
        invoker_id: str,
        *,
        thread_id: Optional[str] = None,
        description: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
        tenant_subdomain: Optional[str] = None,
    ) -> ThreadRegistryEntry:
        ttl = self._ttl(ttl_seconds)
        _validate_ttl(ttl)

        body: dict[str, Any] = {"agentId": agent_id, "invokerId": invoker_id}
        if thread_id is not None:
            body["threadId"] = thread_id
        if description is not None:
            body["description"] = description
        if ttl is not None:
            body["threadTtl"] = ttl
        if metadata is not None:
            body["metadata"] = metadata

        try:
            data = self._request(
                HttpMethod.POST,
                _THREAD_COLLECTION,
                json=body,
                tenant_subdomain=tenant_subdomain,
            )
        except AgentMemoryHttpError as exc:
            if thread_id is not None and exc.status_code == 409:
                if _is_expired_response(exc):
                    _raise_thread_expired(thread_id, from_exc=exc)
                _raise_thread_conflict(thread_id, from_exc=exc)
            raise

        return _parse_entry(data)

    # ------------------------------------------------------------------
    # get_thread
    # ------------------------------------------------------------------

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_GET_THREAD)
    def get_thread(
        self,
        thread_id: str,
        *,
        tenant_subdomain: Optional[str] = None,
    ) -> ThreadRegistryEntry:
        return self._get_thread(thread_id, tenant_subdomain=tenant_subdomain)

    def _get_thread(
        self,
        thread_id: str,
        *,
        tenant_subdomain: Optional[str] = None,
    ) -> ThreadRegistryEntry:
        # Undecorated implementation shared by the public get_thread and by
        # update_thread, so a single update_thread emits exactly one metric
        # (update_thread) rather than also recording a nested get_thread.
        try:
            data = self._request(
                HttpMethod.GET,
                _odata_entity_path(thread_id),
                tenant_subdomain=tenant_subdomain,
            )
        except AgentMemoryNotFoundError as exc:
            raise AgentMemoryThreadNotFoundError(
                f"Thread '{thread_id}' not found"
            ) from exc
        return _parse_entry(data)

    # ------------------------------------------------------------------
    # list_threads
    # ------------------------------------------------------------------

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_LIST_THREADS)
    def list_threads(
        self,
        *,
        agent_id: Optional[str] = None,
        invoker_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        tenant_subdomain: Optional[str] = None,
    ) -> ThreadPage:
        # Validate limit and offset before the limit==0 early-return.
        # The bool guard must come first: False == 0 in Python, so without it
        # limit=False would bypass validation and return an empty page silently.
        if limit is not None:
            if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
                raise ValueError(f"limit must be a non-negative integer, got {limit!r}")
        resolved_offset = 0 if offset is None else offset
        if (
            not isinstance(resolved_offset, int)
            or isinstance(resolved_offset, bool)
            or resolved_offset < 0
        ):
            raise ValueError(f"offset must be a non-negative integer, got {offset!r}")
        if limit is not None and limit == 0:
            path = _build_list_path(agent_id, invoker_id, 0, resolved_offset)
            body = self._request(
                HttpMethod.GET, path, tenant_subdomain=tenant_subdomain
            )
            return ThreadPage(
                entries=[],
                total=body.get("@odata.count", 0),
                limit=0,
                offset=resolved_offset,
            )

        if limit is not None:
            path = _build_list_path(agent_id, invoker_id, limit, resolved_offset)
            body = self._request(
                HttpMethod.GET, path, tenant_subdomain=tenant_subdomain
            )
            return ThreadPage(
                entries=[_parse_entry(row) for row in body.get("value", [])],
                total=body.get("@odata.count", 0),
                limit=limit,
                offset=resolved_offset,
            )

        # Unbounded — follow @odata.nextLink to collect all pages.
        path = _build_list_path(agent_id, invoker_id, None, resolved_offset)
        body = self._request(HttpMethod.GET, path, tenant_subdomain=tenant_subdomain)
        total = body.get("@odata.count", 0)
        entries = [_parse_entry(row) for row in body.get("value", [])]
        next_link: Optional[str] = body.get("@odata.nextLink")
        while next_link:
            body = self._request(
                HttpMethod.GET,
                self._strip_base(next_link),
                tenant_subdomain=tenant_subdomain,
            )
            entries.extend(_parse_entry(row) for row in body.get("value", []))
            next_link = body.get("@odata.nextLink")
        return ThreadPage(
            entries=entries,
            total=total,
            limit=len(entries),
            offset=resolved_offset,
        )

    # ------------------------------------------------------------------
    # update_thread
    # ------------------------------------------------------------------

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_UPDATE_THREAD)
    def update_thread(
        self,
        thread_id: str,
        *,
        description: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
        tenant_subdomain: Optional[str] = None,
    ) -> ThreadRegistryEntry:
        # PATCH-style merge: only fields the caller passed are sent. In
        # particular the registry default TTL is NOT reapplied here — a
        # description-only update must not silently reset the thread's TTL.
        body: dict[str, Any] = {}
        if description is not None:
            body["description"] = description
        if metadata is not None:
            body["metadata"] = metadata
        if ttl_seconds is not None:
            _validate_ttl(ttl_seconds)
            body["threadTtl"] = ttl_seconds

        try:
            self._request(
                HttpMethod.PATCH,
                _odata_entity_path(thread_id),
                json=body,
                tenant_subdomain=tenant_subdomain,
            )
        except AgentMemoryNotFoundError as exc:
            raise AgentMemoryThreadNotFoundError(
                f"Thread '{thread_id}' not found"
            ) from exc

        return self._get_thread(thread_id, tenant_subdomain=tenant_subdomain)

    # ------------------------------------------------------------------
    # delete_thread
    # ------------------------------------------------------------------

    @record_metrics(Module.AGENT_MEMORY, Operation.AGENT_MEMORY_DELETE_THREAD)
    def delete_thread(
        self,
        thread_id: str,
        *,
        tenant_subdomain: Optional[str] = None,
    ) -> None:
        try:
            self._request(
                HttpMethod.DELETE,
                _odata_entity_path(thread_id),
                tenant_subdomain=tenant_subdomain,
            )
        except AgentMemoryNotFoundError:
            logger.debug(
                "delete_thread: thread %r not found, treating as no-op", thread_id
            )
