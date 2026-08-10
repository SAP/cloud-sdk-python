"""Cache isolation strategy and key construction."""

from __future__ import annotations

import hashlib
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class IsolationStrategy(str, Enum):
    """Controls how cache keys are scoped to tenants and users.

    ``TENANT``
        One namespace per tenant. Used when no user context is present.

    ``TENANT_USER``
        One namespace per (tenant, user) pair. Prevents cross-user cache hits
        within the same tenant.
    """

    TENANT = "tenant"
    TENANT_USER = "tenant_user"


def build_isolation_key(
    tenant_id: str,
    user_id: str | None = None,
    strategy: IsolationStrategy | None = None,
) -> str:
    """Derive a cache isolation key from tenant/user context.

    When *strategy* is ``None``, the strategy is selected automatically:
    ``TENANT_USER`` if *user_id* is non-empty, ``TENANT`` otherwise.

    Downgrading explicitly from ``TENANT_USER`` to ``TENANT`` when a
    *user_id* is available risks cross-user contamination and triggers a
    warning.

    Args:
        tenant_id: The tenant identifier (required, non-empty).
        user_id: Optional user identifier. Drives auto-selection when
            *strategy* is ``None``.
        strategy: Explicit override. ``None`` means auto-detect.

    Returns:
        An opaque string suitable for inclusion in a cache key.
    """
    has_user = bool(user_id)
    effective = strategy

    if effective is None:
        effective = (
            IsolationStrategy.TENANT_USER if has_user else IsolationStrategy.TENANT
        )
    elif effective is IsolationStrategy.TENANT and has_user:
        logger.warning(
            "cache isolation downgraded from TENANT_USER to TENANT while user_id is "
            "present — this may cause cross-user cache contamination"
        )

    if effective is IsolationStrategy.TENANT_USER and has_user:
        material = f"{tenant_id}|{user_id}"
        return hashlib.sha256(material.encode()).hexdigest()[:32]

    return tenant_id
