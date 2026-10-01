import re


_SUBDOMAIN_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?$")


def _validate_tenant_subdomain(tenant_subdomain: str | None) -> None:
    """Validate that *tenant_subdomain* is a single RFC 1123 DNS label.

    A valid label contains only ASCII letters, digits, and hyphens, must not
    start or end with a hyphen, and is at most 63 characters long.
    If *tenant_subdomain* is ``None``, the call is a no-op.

    Raises:
        ValueError: If *tenant_subdomain* does not match the expected format.
    """
    if tenant_subdomain is None:
        return
    if not _SUBDOMAIN_RE.fullmatch(tenant_subdomain):
        raise ValueError(f"Invalid tenant_subdomain: {tenant_subdomain!r}")
