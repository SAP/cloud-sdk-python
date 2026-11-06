"""Built-in JWKS-backed IAS JWT verifier."""

import json
import logging
import os
from dataclasses import dataclass
from typing import Optional

import jwt
from jwt import PyJWKClient

from sap_cloud_sdk.core.secret_resolver.resolver import (
    read_from_mount_and_fallback_to_env_var as _read_secret,
)
from sap_cloud_sdk.ias._token import VerifiedIASClaims, parse_token
from sap_cloud_sdk.ias.exceptions import IASTokenError

logger = logging.getLogger(__name__)

_ENV_IAS_URL = "IAS_URL"
_ENV_IAS_CLIENT_ID = "IAS_CLIENT_ID"

_SECRET_MOUNT_BASE = "/etc/secrets/appfnd"
_ENV_VAR_BASE = "CLOUD_SDK_CFG"
_SECRET_MODULE = "identity-service"
_SECRET_DEFAULT_INSTANCE = "default"

_NO_CLIENT_ID_HINT = (
    "the audience (aud) claim cannot be validated. from_env() refuses to build a "
    "verifier that silently accepts tokens issued for any application. Add a "
    "clientid to the binding, or — only if you intentionally accept any audience "
    "— construct the verifier explicitly: IASVerifier(ias_url=..., client_id=None)."
)


@dataclass
class _IASBindingData:
    url: str = ""
    clientid: str = ""


class IASConfigError(Exception):
    """Raised when IAS configuration cannot be resolved from the environment."""


class IASVerifier:
    """JWKS-backed IAS JWT verifier.

    Verifies the JWT signature using the IAS JWKS endpoint and validates
    issuer, expiration, and not-before constraints. Optionally validates
    the audience (``aud`` claim) against the application's client ID.

    Designed to be instantiated once at application startup and shared across
    requests. ``PyJWKClient`` caches keys internally and handles key rotation
    transparently.

    Args:
        ias_url:   IAS tenant base URL, e.g. ``https://<tenant>.accounts.ondemand.com``.
                   The JWKS endpoint is derived as ``{ias_url}/oauth2/certs``.
        client_id: Expected ``aud`` claim (the application's client ID in IAS).
                   When provided, tokens issued for other applications are rejected.
                   When ``None``, audience validation is skipped — an explicit
                   opt-out. :meth:`from_env` never produces this state silently;
                   it raises :class:`IASConfigError` if a binding lacks a clientid.

    Usage::

        from sap_cloud_sdk.ias import IASVerifier

        # Auto-configure from the IAS service binding (recommended)
        verifier = IASVerifier.from_env()

        # Or configure explicitly
        verifier = IASVerifier(
            ias_url="https://mytenant.accounts.ondemand.com",
            client_id="my-app-client-id",
        )

        # Use as a TokenVerifier callable
        verified = verifier("Bearer <token>")
        print(verified.claims.sap_gtid)
    """

    def __init__(self, ias_url: str, client_id: Optional[str] = None) -> None:
        self._ias_url = ias_url.rstrip("/")
        self._client_id = client_id
        jwks_url = f"{self._ias_url}/oauth2/certs"
        self._jwk_client = PyJWKClient(jwks_url, cache_keys=True)
        logger.debug(
            "IASVerifier initialised (jwks=%s, client_id=%s)",
            jwks_url,
            client_id or "<not configured>",
        )

    @classmethod
    def from_env(cls) -> "IASVerifier":
        """Auto-configure from the SAP BTP Identity service binding.

        Lookup order:

        1. ``VCAP_SERVICES`` (Cloud Foundry) —
           ``identity[0].credentials.{url, clientid}``
        2. Kubernetes volume mount — ``/etc/secrets/appfnd/identity-service/default/{url,clientid}``
           (mounted automatically by the agent deployment template)
        3. ``IAS_URL`` + ``IAS_CLIENT_ID`` environment variables (manual / legacy)

        Returns:
            A configured :class:`IASVerifier` instance.

        Raises:
            IASConfigError: when no IAS configuration can be resolved, or when a
                binding is resolved but carries no ``clientid`` (audience would be
                unverifiable). To intentionally accept any audience, construct the
                verifier explicitly with ``IASVerifier(ias_url=..., client_id=None)``.
        """
        vcap_raw = os.getenv("VCAP_SERVICES")
        if vcap_raw:
            try:
                vcap = json.loads(vcap_raw)
                for svc_name in ("identity", "xsuaa"):
                    bindings = vcap.get(svc_name, [])
                    if bindings:
                        creds = bindings[0].get("credentials", {})
                        url = creds.get("url") or creds.get("issuer")
                        client_id = creds.get("clientid")
                        if url:
                            if not client_id:
                                raise IASConfigError(
                                    f"IAS binding VCAP_SERVICES[{svc_name}] has no "
                                    f"'clientid'; {_NO_CLIENT_ID_HINT}"
                                ) from None
                            logger.debug(
                                "IASVerifier.from_env: configured from VCAP_SERVICES[%s]",
                                svc_name,
                            )
                            return cls(ias_url=url, client_id=client_id)
            except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
                logger.debug("IASVerifier.from_env: VCAP_SERVICES parse error: %s", exc)

        # Step 2 — Kubernetes volume mount (identity-service secret)
        binding = _IASBindingData()
        try:
            _read_secret(
                base_volume_mount=_SECRET_MOUNT_BASE,
                base_var_name=_ENV_VAR_BASE,
                module=_SECRET_MODULE,
                instance=_SECRET_DEFAULT_INSTANCE,
                target=binding,
            )
        except Exception as exc:
            logger.debug("IASVerifier.from_env: secret mount lookup failed: %s", exc)
        if binding.url:
            if not binding.clientid:
                raise IASConfigError(
                    f"IAS identity-service secret mount has no 'clientid'; "
                    f"{_NO_CLIENT_ID_HINT}"
                ) from None
            logger.debug(
                "IASVerifier.from_env: configured from Kubernetes secret mount"
            )
            return cls(ias_url=binding.url, client_id=binding.clientid)

        ias_url = os.getenv(_ENV_IAS_URL)
        if ias_url:
            client_id = os.getenv(_ENV_IAS_CLIENT_ID)
            if not client_id:
                raise IASConfigError(
                    f"{_ENV_IAS_URL} is set but {_ENV_IAS_CLIENT_ID} is missing; "
                    f"{_NO_CLIENT_ID_HINT}"
                ) from None
            logger.debug("IASVerifier.from_env: configured from env vars")
            return cls(ias_url=ias_url, client_id=client_id)

        raise IASConfigError(
            f"Cannot auto-configure IASVerifier: no IAS service binding found. "
            f"Set VCAP_SERVICES (CF), mount the identity-service secret at "
            f"{_SECRET_MOUNT_BASE}/{_SECRET_MODULE}/{_SECRET_DEFAULT_INSTANCE}/ (Kubernetes), "
            f"or set {_ENV_IAS_URL} (and optionally {_ENV_IAS_CLIENT_ID}) manually."
        ) from None

    def __call__(self, authorization: str) -> VerifiedIASClaims:
        """Verify the token and return its claims.

        Args:
            authorization: Raw ``Authorization`` header value.
                Accepts ``"Bearer <token>"`` or a bare token string.

        Returns:
            :class:`~sap_cloud_sdk.ias.VerifiedIASClaims` on success.

        Raises:
            IASTokenError: if the token fails any validation check.
        """
        raw = authorization.removeprefix("Bearer ").removeprefix("bearer ").strip()
        try:
            signing_key = self._jwk_client.get_signing_key_from_jwt(raw)

            options: dict = {"require": ["exp", "iss"]}
            decode_kwargs: dict = {
                "algorithms": ["RS256", "ES256"],
                "issuer": self._ias_url,
                "options": options,
            }
            if self._client_id:
                decode_kwargs["audience"] = self._client_id
                options["require"].append("aud")
            else:
                options["verify_aud"] = False

            jwt.decode(raw, signing_key.key, **decode_kwargs)

        except jwt.exceptions.PyJWTError as exc:
            raise IASTokenError(f"IAS JWT verification failed: {exc}") from exc

        return VerifiedIASClaims(claims=parse_token(raw))
