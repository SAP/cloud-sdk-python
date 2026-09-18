"""Low-level HTTP transport for the CBC (Central Business Configuration) module.

Provides:
- :class:`_LazyCertTransport` — httpx transport that defers mTLS cert loading
  until the first real connection, so clients can be constructed with cert data
  that has not yet been written to disk.
"""

from __future__ import annotations

import contextlib
import os
import ssl

import httpx


class _LazyCertTransport(httpx.BaseTransport):
    """httpx transport that defers ``ssl.SSLContext.load_cert_chain`` until first use.

    Cert files are not validated at construction time — the chain is loaded once,
    lazily, before the first real HTTP connection.  This allows :class:`DefaultClient`
    to be instantiated with cert paths that are written after construction (e.g. in
    tests), and avoids I/O at import time.

    Args:
        cert_file: Path to the PEM-encoded client certificate file.
        key_file: Path to the PEM-encoded private key file.
        delete_after_load: When ``True``, both files are deleted from disk after
            the cert chain is loaded.  Use for temporary files written from
            in-memory PEM strings.
    """

    def __init__(
        self, cert_file: str, key_file: str, *, delete_after_load: bool = False
    ) -> None:
        self._cert_file = cert_file
        self._key_file = key_file
        self._delete_after_load = delete_after_load
        self._inner: httpx.HTTPTransport | None = None
        self._files_deleted = False

    def _ensure_inner(self) -> httpx.HTTPTransport:
        if self._inner is None:
            ctx = ssl.create_default_context()
            ctx.load_cert_chain(certfile=self._cert_file, keyfile=self._key_file)
            if self._delete_after_load:
                os.unlink(self._cert_file)
                os.unlink(self._key_file)
                self._files_deleted = True
            self._inner = httpx.HTTPTransport(verify=ctx)
        return self._inner

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return self._ensure_inner().handle_request(request)

    def close(self) -> None:
        if self._delete_after_load and not self._files_deleted:
            with contextlib.suppress(OSError):
                os.unlink(self._cert_file)
            with contextlib.suppress(OSError):
                os.unlink(self._key_file)
            self._files_deleted = True
        if self._inner is not None:
            self._inner.close()
