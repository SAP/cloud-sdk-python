"""OData v4 ``$batch`` request builder and response parser.

OData v4 allows bundling multiple operations into a single HTTP request,
reducing round-trips for bulk reads or transactional write sequences.

This module provides:

* :class:`ODataBatchBuilder` — fluent builder that produces the multipart body.
* :class:`ODataBatchResponse` — parses the server's multipart response.
* :class:`ODataBatchPart` — a single parsed response part.

Wire format (RFC 2046 multipart / OData v4 §11.7):

.. code-block:: http

    POST /odata/v4/DocumentService/$batch HTTP/1.1
    Content-Type: multipart/mixed; boundary=batch_abc123

    --batch_abc123
    Content-Type: application/http

    GET Documents?$filter=... HTTP/1.1
    Accept: application/json

    --batch_abc123
    Content-Type: application/http

    POST DocumentRelations HTTP/1.1
    Content-Type: application/json

    {"DocumentRelationID": "...", ...}
    --batch_abc123--

Usage::

    from sap_cloud_sdk.core.http import ODataBatchBuilder
    import requests, uuid

    builder = (
        ODataBatchBuilder()
        .add_get("Documents", params={"$filter": "DocumentName eq 'test.pdf'"})
        .add_get("DocumentRelations('abc-123')")
    )
    content_type, body = builder.build()

    session = requests.Session()
    resp = session.post(
        "https://adm.example.com/odata/v4/DocumentService/$batch",
        headers={
            "Authorization": "Bearer ...",
            "Content-Type": content_type,
        },
        data=body,
    )
    batch_resp = ODataBatchResponse.parse(
        resp.headers["Content-Type"], resp.text
    )
    for part in batch_resp.parts:
        print(part.status, part.body)
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class _BatchPart:
    """Internal representation of a single request part before serialisation."""

    method: str
    path: str
    headers: Dict[str, str]
    body: Optional[str]


@dataclass
class ODataBatchPart:
    """A single parsed part from an OData ``$batch`` response.

    Attributes:
        status: HTTP status code of this part (e.g. 200, 201, 404).
        headers: Response headers for this part.
        body: Parsed JSON body dict, or ``None`` if the part has no body.
        raw_body: Raw string body before JSON parsing.
    """

    status: int
    headers: Dict[str, str]
    body: Optional[Dict[str, Any]]
    raw_body: str = ""

    @property
    def ok(self) -> bool:
        """``True`` when ``200 <= status < 300``."""
        return 200 <= self.status < 300


class ODataBatchBuilder:
    """Fluent builder for OData v4 ``$batch`` multipart request bodies.

    Each ``add_*`` method appends one operation to the batch and returns
    ``self`` for method chaining.  Call :meth:`build` to get the
    ``(Content-Type header value, body string)`` tuple ready for posting.

    Change sets (atomic write groups) are supported via
    :meth:`begin_change_set` / :meth:`end_change_set`.

    Example::

        builder = (
            ODataBatchBuilder()
            .add_get("Documents", params={"$top": "5"})
            .begin_change_set()
            .add_post("DocumentRelations", body={"...": "..."})
            .end_change_set()
        )
        content_type, body = builder.build()
    """

    def __init__(self, boundary: Optional[str] = None) -> None:
        self._boundary = boundary or f"batch_{uuid.uuid4().hex}"
        self._parts: List[_BatchPart | _ChangeSet] = []
        self._current_cs: Optional[_ChangeSet] = None

    # ------------------------------------------------------------------
    # Read operations (outside changeset)
    # ------------------------------------------------------------------

    def add_get(
        self,
        path: str,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> "ODataBatchBuilder":
        """Append a GET operation to the batch.

        Args:
            path: OData resource path (e.g. ``"Documents"`` or
                  ``"Documents('id-123')"``).
            params: URL query parameters (``$filter``, ``$expand``, etc.).
            headers: Extra request headers for this part.
        """
        if self._current_cs is not None:
            raise RuntimeError(
                "Cannot add_get inside a change set. Call end_change_set() first."
            )
        full_path = _build_path(path, params)
        h = {"Accept": "application/json"}
        if headers:
            h.update(headers)
        self._parts.append(
            _BatchPart(method="GET", path=full_path, headers=h, body=None)
        )
        return self

    # ------------------------------------------------------------------
    # Write operations (inside or outside changeset)
    # ------------------------------------------------------------------

    def add_post(
        self,
        path: str,
        body: Any,
        headers: Optional[Dict[str, str]] = None,
    ) -> "ODataBatchBuilder":
        """Append a POST (create) operation."""
        return self._add_write("POST", path, body, headers)

    def add_patch(
        self,
        path: str,
        body: Any,
        headers: Optional[Dict[str, str]] = None,
    ) -> "ODataBatchBuilder":
        """Append a PATCH (update) operation."""
        return self._add_write("PATCH", path, body, headers)

    def add_put(
        self,
        path: str,
        body: Any,
        headers: Optional[Dict[str, str]] = None,
    ) -> "ODataBatchBuilder":
        """Append a PUT (replace) operation."""
        return self._add_write("PUT", path, body, headers)

    def add_delete(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> "ODataBatchBuilder":
        """Append a DELETE operation."""
        return self._add_write("DELETE", path, None, headers)

    # ------------------------------------------------------------------
    # Change set support (atomic write groups)
    # ------------------------------------------------------------------

    def begin_change_set(self, boundary: Optional[str] = None) -> "ODataBatchBuilder":
        """Start a change set (all contained writes succeed or fail atomically).

        Raises:
            RuntimeError: If a change set is already open.
        """
        if self._current_cs is not None:
            raise RuntimeError(
                "A change set is already open. Call end_change_set() first."
            )
        self._current_cs = _ChangeSet(
            boundary=boundary or f"changeset_{uuid.uuid4().hex}"
        )
        return self

    def end_change_set(self) -> "ODataBatchBuilder":
        """Close the current change set and add it to the batch.

        Raises:
            RuntimeError: If no change set is open.
        """
        if self._current_cs is None:
            raise RuntimeError("No change set is open. Call begin_change_set() first.")
        self._parts.append(self._current_cs)
        self._current_cs = None
        return self

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self) -> Tuple[str, str]:
        """Serialise the batch into an HTTP body.

        Returns:
            A ``(content_type, body)`` tuple where *content_type* is the
            value for the ``Content-Type`` request header (including the
            boundary parameter) and *body* is the complete multipart body
            string to send.

        Raises:
            RuntimeError: If a change set is still open (not ended).
        """
        if self._current_cs is not None:
            raise RuntimeError(
                "Unclosed change set. Call end_change_set() before build()."
            )

        lines: List[str] = []
        for part in self._parts:
            lines.append(f"--{self._boundary}")
            if isinstance(part, _ChangeSet):
                lines.extend(part.serialise())
            else:
                lines.extend(_serialise_part(part))
        lines.append(f"--{self._boundary}--")
        body = "\r\n".join(lines)
        content_type = f"multipart/mixed; boundary={self._boundary}"
        return content_type, body

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _add_write(
        self,
        method: str,
        path: str,
        body: Optional[Any],
        extra_headers: Optional[Dict[str, str]],
    ) -> "ODataBatchBuilder":
        target = self._current_cs if self._current_cs is not None else self
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if extra_headers:
            h.update(extra_headers)
        body_str = json.dumps(body) if body is not None else None
        part = _BatchPart(method=method, path=path, headers=h, body=body_str)
        if isinstance(target, _ChangeSet):
            target.parts.append(part)
        else:
            self._parts.append(part)
        return self


class _ChangeSet:
    """Internal representation of an OData ``$batch`` change set."""

    def __init__(self, boundary: str) -> None:
        self.boundary = boundary
        self.parts: List[_BatchPart] = []

    def serialise(self) -> List[str]:
        lines = [
            f"Content-Type: multipart/mixed; boundary={self.boundary}",
            "",
        ]
        for part in self.parts:
            lines.append(f"--{self.boundary}")
            lines.extend(_serialise_part(part))
        lines.append(f"--{self.boundary}--")
        return lines


def _serialise_part(part: _BatchPart) -> List[str]:
    """Serialise a single ``application/http`` batch part."""
    lines = [
        "Content-Type: application/http",
        "Content-Transfer-Encoding: binary",
        "",
        f"{part.method} {part.path} HTTP/1.1",
    ]
    for k, v in part.headers.items():
        lines.append(f"{k}: {v}")
    lines.append("")  # blank line separating headers from body
    if part.body is not None:
        lines.append(part.body)
    return lines


def _build_path(path: str, params: Optional[Dict[str, str]]) -> str:
    """Append query string to *path* if *params* is non-empty."""
    if not params:
        return path
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{path}?{qs}"


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------


class ODataBatchResponse:
    """Parses an OData v4 ``$batch`` multipart response.

    Args:
        parts: Parsed :class:`ODataBatchPart` items.

    Usage::

        batch_resp = ODataBatchResponse.parse(content_type, response_body)
        for part in batch_resp.parts:
            if not part.ok:
                print(f"Failed: {part.status} {part.body}")
    """

    def __init__(self, parts: List[ODataBatchPart]) -> None:
        self.parts = parts

    def __iter__(self):
        return iter(self.parts)

    def __len__(self) -> int:
        return len(self.parts)

    @classmethod
    def parse(cls, content_type: str, body: str) -> "ODataBatchResponse":
        """Parse an OData ``$batch`` HTTP response.

        Args:
            content_type: The value of the response ``Content-Type`` header
                (e.g. ``"multipart/mixed; boundary=batch_abc"``).
            body: The raw response body string.

        Returns:
            An :class:`ODataBatchResponse` with all parsed parts.

        Raises:
            ValueError: If the boundary parameter cannot be found in *content_type*.
        """
        boundary = _extract_boundary(content_type)
        parts = _parse_parts(boundary, body)
        return cls(parts)


def _extract_boundary(content_type: str) -> str:
    # Try quoted form first: boundary="some value with spaces"
    m = re.search(r'boundary="([^"]+)"', content_type, re.IGNORECASE)
    if m:
        return m.group(1)
    # Unquoted form: boundary=batch_abc (no spaces/semicolons)
    m = re.search(r'boundary=([^\s;"]+)', content_type, re.IGNORECASE)
    if m:
        return m.group(1)
    raise ValueError(f"No boundary found in Content-Type: {content_type!r}")


def _parse_parts(boundary: str, body: str) -> List[ODataBatchPart]:
    """Split the multipart body on *boundary* and parse each HTTP sub-response."""
    delimiter = f"--{boundary}"
    segments = body.split(delimiter)
    parts: List[ODataBatchPart] = []

    for segment in segments:
        segment = segment.strip()
        if not segment or segment == "--":
            continue
        # Each segment may itself be a changeset (nested multipart)
        if "multipart/mixed" in segment:
            inner_ct_match = re.search(
                r"Content-Type:\s*(multipart/mixed[^\r\n]*)", segment, re.IGNORECASE
            )
            if inner_ct_match:
                inner_ct = inner_ct_match.group(1)
                inner_body_start = segment.find("\r\n\r\n")
                if inner_body_start == -1:
                    inner_body_start = segment.find("\n\n")
                inner_body = (
                    segment[inner_body_start:].strip()
                    if inner_body_start != -1
                    else segment
                )
                parts.extend(_parse_parts(_extract_boundary(inner_ct), inner_body))
            continue

        parsed = _parse_http_part(segment)
        if parsed is not None:
            parts.append(parsed)

    return parts


def _parse_http_part(segment: str) -> Optional[ODataBatchPart]:
    """Parse a single ``application/http`` segment into an :class:`ODataBatchPart`."""
    # Find the embedded HTTP response line (e.g. "HTTP/1.1 200 OK")
    http_match = re.search(r"HTTP/1\.[01]\s+(\d+)[^\r\n]*", segment)
    if not http_match:
        return None

    status = int(http_match.group(1))
    # Everything after the HTTP status line
    after_status = segment[http_match.end() :].lstrip("\r\n")

    # Split headers from body
    header_end = after_status.find("\r\n\r\n")
    if header_end == -1:
        header_end = after_status.find("\n\n")
        sep_len = 2
    else:
        sep_len = 4

    if header_end == -1:
        headers_str, raw_body = after_status, ""
    else:
        headers_str = after_status[:header_end]
        raw_body = after_status[header_end + sep_len :]

    # Parse headers
    headers: Dict[str, str] = {}
    for line in re.split(r"\r?\n", headers_str):
        if ":" in line:
            k, _, v = line.partition(":")
            headers[k.strip()] = v.strip()

    # Parse JSON body
    body: Optional[Dict[str, Any]] = None
    raw_body = raw_body.strip()
    if raw_body:
        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError:
            pass  # non-JSON body — leave body=None, raw_body has it

    return ODataBatchPart(status=status, headers=headers, body=body, raw_body=raw_body)
