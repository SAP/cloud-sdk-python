"""Client-certificate loading for mTLS destinations.

Parses PEM and PKCS12 keystores from the Destination Service v2 certificate
payload and builds a stdlib ssl.SSLContext for mTLS.

Supported formats (selected by the file extension of Certificate.name):
  pem   — combined PEM bundle (cert + optional chain + private key; key may be
           encrypted via KeyStorePassword)
  p12   — PKCS12 binary keystore (requires KeyStorePassword in practice)
  pfx   — PKCS12 binary keystore (alternate extension)

"""

from __future__ import annotations

import base64
import binascii
import os
import ssl
import tempfile
from typing import Optional

from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
)
from cryptography.hazmat.primitives.serialization import pkcs12

from sap_cloud_sdk.destination._models import Authentication, Certificate, Destination
from sap_cloud_sdk.destination.exceptions import DestinationCertificateError

_SUPPORTED_EXTENSIONS = frozenset({"pem", "p12", "pfx"})


def build_client_cert_context(destination: Destination) -> Optional[ssl.SSLContext]:
    """Return an mTLS SSL context for the destination, or None if not applicable.

    Returns None when:
    - The destination does not use ClientCertificateAuthentication.
    - The certificate list contains no PEM/PKCS12 entry and no KeyStoreLocation is set.

    Raises DestinationCertificateError when client-cert auth is required but no
    usable certificate can be loaded (wrong format, malformed content, key mismatch).
    """
    if not _is_client_certificate_auth(destination):
        return None

    cert = _select_certificate(destination)
    if cert is None:
        raise DestinationCertificateError(
            f"Destination '{destination.name}' uses ClientCertificateAuthentication "
            "but no usable certificate is available in the destination's certificate list."
        )

    try:
        return _load_cert_into_context(cert, destination)
    except DestinationCertificateError:
        raise
    except Exception as e:
        raise DestinationCertificateError(
            f"Failed to load client certificate '{cert.name}': {e}"
        ) from e


def _is_client_certificate_auth(destination: Destination) -> bool:
    auth = destination.authentication
    auth_value = getattr(auth, "value", auth)
    return str(auth_value) == Authentication.CLIENT_CERTIFICATE_AUTHENTICATION.value


def _select_certificate(destination: Destination) -> Optional[Certificate]:
    certs = destination.certificates
    if not certs:
        return None

    props = destination.properties or {}
    ks_location = props.get("KeyStoreLocation")

    if ks_location:
        for cert in certs:
            if cert.name == ks_location:
                ext = cert.name.rsplit(".", 1)[-1].lower() if "." in cert.name else ""
                if ext not in _SUPPORTED_EXTENSIONS:
                    raise DestinationCertificateError(
                        f"Certificate '{cert.name}' has unsupported format '.{ext}'. "
                        f"Supported formats: {sorted(_SUPPORTED_EXTENSIONS)}. "
                        "JKS is not supported (Java-specific format)."
                    )
                return cert
        return None

    for cert in certs:
        ext = cert.name.rsplit(".", 1)[-1].lower() if "." in cert.name else ""
        if ext in _SUPPORTED_EXTENSIONS:
            return cert

    return None


def _load_cert_into_context(
    cert: Certificate, destination: Destination
) -> ssl.SSLContext:
    ext = cert.name.rsplit(".", 1)[-1].lower() if "." in cert.name else ""
    password = _get_key_password(destination)

    if ext == "pem":
        return _load_pem(cert.content, password, cert.name)

    if ext in ("p12", "pfx"):
        return _load_pkcs12(cert.content, password, cert.name)

    raise DestinationCertificateError(
        f"Certificate '{cert.name}' has unsupported format '.{ext}'. "
        f"Supported: {sorted(_SUPPORTED_EXTENSIONS)}."
    )


def _load_pem(content: str, password: Optional[bytes], name: str) -> ssl.SSLContext:
    pem = _decode_pem_bytes(content, name)
    return _build_context(pem, password)


def _load_pkcs12(content: str, password: Optional[bytes], name: str) -> ssl.SSLContext:
    try:
        der = base64.b64decode(content)
    except (binascii.Error, ValueError) as e:
        raise DestinationCertificateError(
            f"Certificate '{name}' content is not valid base64: {e}"
        ) from e

    try:
        private_key, leaf, extra_certs = pkcs12.load_key_and_certificates(der, password)
    except Exception as e:
        raise DestinationCertificateError(
            f"Failed to load PKCS12 certificate '{name}': {e}"
        ) from e

    if leaf is None or private_key is None:
        raise DestinationCertificateError(
            f"PKCS12 certificate '{name}' is missing a certificate or private key."
        )

    # PKCS12 gives us parsed objects (no file), so serialize leaf + chain + an
    # unencrypted key into a single PEM bundle. The key is already decrypted by
    # load_key_and_certificates, so no password is passed to _build_context.
    key_pem = private_key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    )
    leaf_pem = leaf.public_bytes(Encoding.PEM)
    chain_pem = b"".join(c.public_bytes(Encoding.PEM) for c in (extra_certs or []))
    return _build_context(leaf_pem + chain_pem + key_pem, password=None)


def _build_context(
    bundle_pem: bytes,
    password: Optional[bytes],
) -> ssl.SSLContext:
    # Write the combined PEM bundle (cert chain + key) to a temp file,
    # load it into an SSLContext, then immediately delete.
    str_password: Optional[str] = password.decode("utf-8") if password else None

    # Guard against an encrypted key with no password
    if str_password is None and any(
        marker in bundle_pem
        for marker in (
            b"-----BEGIN ENCRYPTED PRIVATE KEY-----",
            b"Proc-Type: 4,ENCRYPTED",
        )
    ):
        raise DestinationCertificateError(
            "The private key is encrypted but no KeyStorePassword was provided."
        )

    fd, path = tempfile.mkstemp(suffix=".pem")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(bundle_pem)
        ctx = ssl.create_default_context()
        ctx.load_cert_chain(path, password=str_password)
    except ssl.SSLError as e:
        if getattr(e, "reason", None) == "KEY_VALUES_MISMATCH":
            raise DestinationCertificateError(
                "The certificate and private key do not match."
            ) from e
        raise DestinationCertificateError(
            "Could not load the client certificate/private key (possible causes: "
            f"wrong password, malformed PEM, or a missing certificate/key block): {e}"
        ) from e
    except OSError as e:
        raise DestinationCertificateError(
            f"Could not load the client certificate/private key: {e}"
        ) from e
    finally:
        os.unlink(path)

    return ctx


def _decode_pem_bytes(content: str, name: str) -> bytes:
    if not content or not content.strip():
        raise DestinationCertificateError(f"Certificate '{name}' content is empty.")

    pem = content.strip()

    if "-----BEGIN " not in pem:
        try:
            decoded = base64.b64decode("".join(pem.split()))
        except (binascii.Error, ValueError) as e:
            raise DestinationCertificateError(
                f"Certificate '{name}' content is not valid base64-encoded PEM: {e}"
            ) from e
        try:
            pem = decoded.decode("utf-8")
        except UnicodeDecodeError as e:
            raise DestinationCertificateError(
                f"Certificate '{name}' content is not valid UTF-8 PEM text."
            ) from e

    return pem.encode("utf-8")


def _get_key_password(destination: Destination) -> Optional[bytes]:
    props = destination.properties or {}
    password = props.get("KeyStorePassword")
    if password and password.strip():
        return password.encode("utf-8")
    return None
