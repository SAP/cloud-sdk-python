import re
from urllib.parse import urlparse, urlunparse


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


def _derive_tenant_token_url(
    token_url: str,
    identityzone: str,
    tenant_subdomain: str,
) -> str:
    """Return *token_url* with the first hostname label replaced by *tenant_subdomain*.

    Only the leading DNS label of the hostname is replaced when it equals
    *identityzone*.  All other URL components (scheme, port, path, query,
    fragment) are preserved verbatim.  If the first label does not match
    *identityzone*, the original URL is returned unchanged.

    Args:
        token_url: The configured OAuth2 token endpoint URL.
        identityzone: Provider identity zone label from the service binding.
        tenant_subdomain: Validated single-label tenant identifier.

    Returns:
        The derived token URL with only the first hostname label swapped.
    """
    parsed = urlparse(token_url)
    host = parsed.hostname or ""
    first_label, sep, rest = host.partition(".")
    if sep and first_label == identityzone:
        new_netloc = f"{tenant_subdomain}.{rest}"
        if parsed.port is not None:
            new_netloc = f"{new_netloc}:{parsed.port}"
        return urlunparse(parsed._replace(netloc=new_netloc))
    return token_url
