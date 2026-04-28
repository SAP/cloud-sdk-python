"""SPIFFE Workload API wrapper for X.509 SVID fetching."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass

from .exceptions import SpiffeError

logger = logging.getLogger(__name__)

try:
    from spiffe import WorkloadApiClient as WorkloadApiClient  # type: ignore
except Exception:
    WorkloadApiClient = None  # type: ignore


@dataclass(frozen=True)
class X509Credentials:
    """PEM-encoded mTLS material obtained from SPIRE via the Workload API.

    Attributes:
        cert_chain_pem: PEM-encoded client certificate chain (leaf first).
        private_key_pem: PEM-encoded private key for the leaf certificate.
        trust_bundle_pem: PEM-encoded CA certificates for server verification.
        spiffe_id: The SPIFFE ID embedded in the leaf certificate.
    """

    cert_chain_pem: bytes
    private_key_pem: bytes
    trust_bundle_pem: bytes
    spiffe_id: str


def _cert_to_pem(cert) -> bytes:
    from cryptography.hazmat.primitives.serialization import Encoding

    return cert.public_bytes(Encoding.PEM)


def _key_to_pem(private_key) -> bytes:
    from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

    return private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())


def fetch_x509_credentials(socket_path: str) -> X509Credentials:
    """Fetch an X.509 SVID from the SPIRE agent via the Workload API.

    Args:
        socket_path: Absolute filesystem path to the SPIFFE Workload API socket.

    Returns:
        An :class:`X509Credentials` with PEM-encoded cert chain, key, and trust bundle.

    Raises:
        SpiffeError: When the SPIRE agent is unreachable or the SVID cannot be fetched.
    """
    if WorkloadApiClient is None or sys.modules.get("spiffe") is None:
        try:
            from spiffe import WorkloadApiClient as _Client  # type: ignore

            globals()["WorkloadApiClient"] = _Client
        except Exception as exc:
            raise SpiffeError(
                "The 'spiffe' package is required for ZTIS authentication. "
                "Install it with: pip install spiffe",
                cause=exc,
            ) from exc

    if not socket_path.startswith("unix:"):
        if not socket_path.startswith("/"):
            socket_path = "/" + socket_path
        spiffe_socket = f"unix://{socket_path}"
    else:
        spiffe_socket = socket_path

    logger.debug("Connecting to SPIFFE Workload API at %s", spiffe_socket)

    try:
        with WorkloadApiClient(spiffe_socket) as client:
            x509_context = client.fetch_x509_context()

            svids = x509_context.x509_svids
            if not svids:
                raise SpiffeError("SPIRE returned an empty X.509 SVID list.")

            svid = svids[0]
            spiffe_id = str(svid.spiffe_id)
            cert_chain_pem = b"".join(_cert_to_pem(c) for c in svid.cert_chain)
            private_key_pem = _key_to_pem(svid.private_key)

            trust_pem_parts: list[bytes] = []
            for bundle in x509_context.x509_bundle_set.bundles.values():
                for authority in bundle.x509_authorities:
                    trust_pem_parts.append(_cert_to_pem(authority))

            trust_bundle_pem = b"".join(trust_pem_parts)

            logger.info(
                "Fetched X.509 SVID  spiffe_id=%s  chain_len=%d  trust_cas=%d",
                spiffe_id,
                len(svid.cert_chain),
                len(trust_pem_parts),
            )

            return X509Credentials(
                cert_chain_pem=cert_chain_pem,
                private_key_pem=private_key_pem,
                trust_bundle_pem=trust_bundle_pem,
                spiffe_id=spiffe_id,
            )

    except SpiffeError:
        raise
    except Exception as exc:
        raise SpiffeError(
            f"Failed to fetch X.509 SVID from SPIRE agent at {spiffe_socket}: {exc}",
            cause=exc,
        ) from exc
