"""Configuration objects for the CBC (Central Business Configuration) module."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CBCDestinationConfig:
    """Destination-Service inputs for :func:`create_agent_client`.

    All three fields select *what to read* from the Destination Service when the
    platform adapter builds a client. Each falls back to its ``CLOUD_SDK_CBC_*``
    env var, then to a platform default, when left ``None``.

    Attributes:
        destination_instance: The ``instance`` passed to the destination
            ``create_fragment_client`` / ``create_certificate_client`` (used for
            secret resolution in cloud mode). Falls back to the
            ``CLOUD_SDK_CBC_DESTINATION_INSTANCE`` env var, else ``"default"``.
        cbc_cert_name: Name of the app's mTLS certificate. Falls back to the
            ``CLOUD_SDK_CBC_CERTIFICATE_NAME`` env var, else derived from the
            platform landscape (``APPFND_CONHOS_LANDSCAPE``).
        p12_password: Certificate keystore password. Falls back to the
            ``CLOUD_SDK_CBC_P12_PASSWORD`` env var, else ``None``.
    """

    destination_instance: str | None = None
    cbc_cert_name: str | None = None
    p12_password: bytes | None = None
