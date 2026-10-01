"""Unit tests for build_client_cert_context (mTLS client-certificate loader)."""

from __future__ import annotations

import base64
import ssl
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption,
    Encoding,
    NoEncryption,
    PrivateFormat,
)
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from sap_cloud_sdk.destination._cert_loader import build_client_cert_context
from sap_cloud_sdk.destination._models import Destination
from sap_cloud_sdk.destination.exceptions import DestinationCertificateError


# ---------------------------------------------------------------------------
# Module-scoped key fixtures (RSA keygen is expensive — reuse across tests)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def rsa_key_a():
    """Generate RSA key A once for the entire module."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="module")
def rsa_key_b():
    """Generate RSA key B once for the entire module."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


# ---------------------------------------------------------------------------
# Module-level helper functions
# ---------------------------------------------------------------------------


def _self_signed(key) -> x509.Certificate:
    """Build a minimal self-signed certificate for the given key."""
    subject = issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "test.example.com")]
    )
    return (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .sign(key, hashes.SHA256())
    )


def _pem_bundle(cert, key, password: bytes | None = None) -> str:
    """Return a PEM string: cert block + private key block (PKCS8).

    If password is given the key is encrypted with BestAvailableEncryption,
    otherwise NoEncryption is used.
    """
    enc_alg = BestAvailableEncryption(password) if password else NoEncryption()
    key_pem = key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=enc_alg,
    )
    cert_pem = cert.public_bytes(Encoding.PEM)
    return (cert_pem + key_pem).decode("utf-8")


def _pkcs12_bytes(cert, key, password: bytes | None) -> str:
    """Return base64-encoded PKCS12 bytes for the given cert/key pair."""
    enc_alg = BestAvailableEncryption(password) if password else NoEncryption()
    der = pkcs12.serialize_key_and_certificates(
        name=b"x",
        key=key,
        cert=cert,
        cas=None,
        encryption_algorithm=enc_alg,
    )
    return base64.b64encode(der).decode("utf-8")


def _dest_with_cert(
    name: str,
    content: str,
    *,
    ks_location: str | None = None,
    ks_password: str | None = None,
) -> Destination:
    """Build a ClientCertificateAuthentication destination with one certificate.

    include_runtime_data=True is required or the certificates list is dropped.
    """
    d: dict = {
        "Name": "d",
        "Type": "HTTP",
        "URL": "https://example.com",
        "Authentication": "ClientCertificateAuthentication",
        "certificates": [{"Name": name, "Content": content}],
    }
    if ks_location is not None:
        d["KeyStoreLocation"] = ks_location
    if ks_password is not None:
        d["KeyStorePassword"] = ks_password
    return Destination.from_dict(d, include_runtime_data=True)


# ---------------------------------------------------------------------------
# TestSelection — certificate selection logic
# ---------------------------------------------------------------------------


class TestSelection:
    """Tests for how build_client_cert_context selects (or skips) a certificate."""

    def test_non_client_cert_auth_returns_none(self):
        """Non-ClientCertificateAuthentication destinations return None."""
        dest = Destination.from_dict(
            {
                "Name": "d",
                "Type": "HTTP",
                "URL": "https://example.com",
                "Authentication": "NoAuthentication",
            }
        )
        assert build_client_cert_context(dest) is None

    def test_client_cert_auth_empty_certificates_raises(self):
        """ClientCertificateAuthentication with no certificates raises."""
        dest = Destination.from_dict(
            {
                "Name": "d",
                "Type": "HTTP",
                "URL": "https://example.com",
                "Authentication": "ClientCertificateAuthentication",
                "certificates": [],
            },
            include_runtime_data=True,
        )
        with pytest.raises(DestinationCertificateError, match="no usable certificate"):
            build_client_cert_context(dest)

    def test_jks_only_cert_raises_unsupported_format(self):
        """A JKS-only certificate list raises DestinationCertificateError."""
        dest = Destination.from_dict(
            {
                "Name": "d",
                "Type": "HTTP",
                "URL": "https://example.com",
                "Authentication": "ClientCertificateAuthentication",
                "certificates": [{"Name": "keystore.jks", "Content": "anycontent"}],
            },
            include_runtime_data=True,
        )
        with pytest.raises(DestinationCertificateError, match="no usable certificate"):
            build_client_cert_context(dest)

    def test_ks_location_selects_specific_cert(self, rsa_key_a, rsa_key_b):
        """KeyStoreLocation picks the named cert when multiple certs are present."""
        cert_a = _self_signed(rsa_key_a)
        cert_b = _self_signed(rsa_key_b)
        bundle_a = _pem_bundle(cert_a, rsa_key_a)
        bundle_b = _pem_bundle(cert_b, rsa_key_b)

        dest = Destination.from_dict(
            {
                "Name": "d",
                "Type": "HTTP",
                "URL": "https://example.com",
                "Authentication": "ClientCertificateAuthentication",
                "KeyStoreLocation": "cert-b.pem",
                "certificates": [
                    {"Name": "cert-a.pem", "Content": bundle_a},
                    {"Name": "cert-b.pem", "Content": bundle_b},
                ],
            },
            include_runtime_data=True,
        )
        ctx = build_client_cert_context(dest)
        assert isinstance(ctx, ssl.SSLContext)


# ---------------------------------------------------------------------------
# TestPemHappy — successful PEM loading
# ---------------------------------------------------------------------------


class TestPemHappy:
    """Tests for successful PEM keystore loading paths."""

    def test_unencrypted_pem_returns_ssl_context(self, rsa_key_a):
        """An unencrypted PEM bundle returns an SSLContext with secure defaults."""
        cert = _self_signed(rsa_key_a)
        bundle = _pem_bundle(cert, rsa_key_a)
        dest = _dest_with_cert("client.pem", bundle)

        ctx = build_client_cert_context(dest)

        assert isinstance(ctx, ssl.SSLContext)
        assert ctx.verify_mode == ssl.CERT_REQUIRED
        assert ctx.check_hostname is True

    def test_encrypted_pem_correct_password_returns_ssl_context(self, rsa_key_a):
        """An encrypted PEM key with the correct KeyStorePassword returns an SSLContext."""
        cert = _self_signed(rsa_key_a)
        bundle = _pem_bundle(cert, rsa_key_a, password=b"s3cr3t")
        dest = _dest_with_cert("client.pem", bundle, ks_password="s3cr3t")

        ctx = build_client_cert_context(dest)

        assert isinstance(ctx, ssl.SSLContext)

    def test_base64_wrapped_pem_is_decoded(self, rsa_key_a):
        """A base64-encoded PEM bundle (no BEGIN header visible) is decoded transparently."""
        cert = _self_signed(rsa_key_a)
        bundle = _pem_bundle(cert, rsa_key_a)
        # Wrap the whole PEM string in base64 — exercises _decode_pem_bytes
        b64_content = base64.b64encode(bundle.encode()).decode("utf-8")
        dest = _dest_with_cert("client.pem", b64_content)

        ctx = build_client_cert_context(dest)

        assert isinstance(ctx, ssl.SSLContext)

    def test_chain_cert_accepted(self, rsa_key_a, rsa_key_b):
        """A PEM bundle with leaf + intermediate cert + key is accepted."""
        leaf_cert = _self_signed(rsa_key_a)
        intermediate_cert = _self_signed(rsa_key_b)  # acts as chain material

        leaf_pem = leaf_cert.public_bytes(Encoding.PEM)
        intermediate_pem = intermediate_cert.public_bytes(Encoding.PEM)
        key_pem = rsa_key_a.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption(),
        )
        # leaf + chain cert + key — matches the pattern ssl.load_cert_chain expects
        bundle = (leaf_pem + intermediate_pem + key_pem).decode("utf-8")
        dest = _dest_with_cert("client.pem", bundle)

        ctx = build_client_cert_context(dest)

        assert isinstance(ctx, ssl.SSLContext)


# ---------------------------------------------------------------------------
# TestPkcs12Happy — successful PKCS12 loading
# ---------------------------------------------------------------------------


class TestPkcs12Happy:
    """Tests for successful PKCS12 keystore loading paths."""

    def test_p12_with_password_returns_ssl_context(self, rsa_key_a):
        """A PKCS12 (.p12) keystore with a password loads successfully."""
        cert = _self_signed(rsa_key_a)
        p12_b64 = _pkcs12_bytes(cert, rsa_key_a, password=b"p12pass")
        dest = _dest_with_cert("client.p12", p12_b64, ks_password="p12pass")

        ctx = build_client_cert_context(dest)

        assert isinstance(ctx, ssl.SSLContext)

    def test_pfx_extension_also_works(self, rsa_key_a):
        """A PKCS12 keystore with .pfx extension is handled identically to .p12."""
        cert = _self_signed(rsa_key_a)
        p12_b64 = _pkcs12_bytes(cert, rsa_key_a, password=b"pfxpass")
        dest = _dest_with_cert("client.pfx", p12_b64, ks_password="pfxpass")

        ctx = build_client_cert_context(dest)

        assert isinstance(ctx, ssl.SSLContext)


# ---------------------------------------------------------------------------
# TestFailures — error paths
# ---------------------------------------------------------------------------


class TestFailures:
    """Tests for DestinationCertificateError error paths."""

    def test_malformed_pem_raises(self):
        """Content that is neither valid PEM nor valid base64 raises DestinationCertificateError."""
        dest = _dest_with_cert("client.pem", "not-a-cert!!!")
        with pytest.raises(DestinationCertificateError):
            build_client_cert_context(dest)

    def test_encrypted_key_wrong_password_raises(self, rsa_key_a):
        """An encrypted PEM key with the wrong password raises DestinationCertificateError."""
        cert = _self_signed(rsa_key_a)
        bundle = _pem_bundle(cert, rsa_key_a, password=b"correct")
        dest = _dest_with_cert("client.pem", bundle, ks_password="wrong")

        with pytest.raises(DestinationCertificateError):
            build_client_cert_context(dest)

    def test_encrypted_key_missing_password_raises_and_does_not_hang(self, rsa_key_a):
        """An encrypted PEM key with no KeyStorePassword raises immediately (no interactive prompt)."""
        cert = _self_signed(rsa_key_a)
        bundle = _pem_bundle(cert, rsa_key_a, password=b"somepass")
        # No ks_password — the loader guards against the interactive-prompt footgun
        dest = _dest_with_cert("client.pem", bundle)

        with pytest.raises(DestinationCertificateError, match="KeyStorePassword"):
            build_client_cert_context(dest)

    def test_cert_key_mismatch_raises(self, rsa_key_a, rsa_key_b):
        """A bundle where cert and private key belong to different keys raises DestinationCertificateError."""
        cert_a = _self_signed(rsa_key_a)
        # cert signed by key_a, but private key is key_b — they don't match
        cert_pem = cert_a.public_bytes(Encoding.PEM)
        key_b_pem = rsa_key_b.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption(),
        )
        bundle = (cert_pem + key_b_pem).decode("utf-8")
        dest = _dest_with_cert("client.pem", bundle)

        with pytest.raises(DestinationCertificateError, match="do not match"):
            build_client_cert_context(dest)

    def test_cert_only_no_key_raises(self, rsa_key_a):
        """A PEM bundle with only a cert block (no private key) raises DestinationCertificateError."""
        cert = _self_signed(rsa_key_a)
        cert_only = cert.public_bytes(Encoding.PEM).decode("utf-8")
        dest = _dest_with_cert("client.pem", cert_only)

        with pytest.raises(DestinationCertificateError):
            build_client_cert_context(dest)
