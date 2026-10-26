"""Cache isolation strategy and key construction."""

from __future__ import annotations

import logging
from enum import Enum

from sap_cloud_sdk.core.runtime_context import APP_TENANT_ID, USER_ID, get_context

logger = logging.getLogger(__name__)


class IsolationStrategy(str, Enum):
    """Controls how cache keys are scoped to tenants and users.

    ``TENANT``
        One namespace per tenant. Suitable for data that is shared across all
        users of a tenant (e.g. configuration, service metadata).

    ``TENANT_USER``
        One namespace per (tenant, user) pair. Prevents cross-user cache hits
        within the same tenant. Use for user-specific data.

    ``PROVIDER``
        A single shared namespace for the whole service, ignoring tenant and
        user context entirely. Use for service-wide data such as CSRF tokens
        or provider-level metadata that is not tenant-specific.
    """

    TENANT = "tenant"
    TENANT_USER = "tenant_user"
    PROVIDER = "provider"


def build_isolation_key(strategy: IsolationStrategy | None = None) -> str:
    """Derive a cache isolation key from the current runtime context.

    Reads ``tenant_id`` and ``user_id`` implicitly from the active
    :func:`~sap_cloud_sdk.core.runtime_context.get_context`.

    When *strategy* is ``None``, the strategy is selected automatically:
    ``TENANT_USER`` if a user ID is present in context, ``TENANT`` otherwise.

    Downgrading explicitly from ``TENANT_USER`` to ``TENANT`` when a user ID
    is available risks cross-user contamination and triggers a warning.

    Args:
        strategy: Explicit override. ``None`` means auto-detect.

    Returns:
        An opaque string suitable for inclusion in a cache key.
    """
    if strategy is IsolationStrategy.PROVIDER:
        return "provider"

    ctx = get_context()
    tenant_id = ctx.get(APP_TENANT_ID)
    user_id = ctx.get(USER_ID)

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
        return f"tenant:{tenant_id}:user:{user_id}"

    return f"tenant:{tenant_id}" if tenant_id else ""
