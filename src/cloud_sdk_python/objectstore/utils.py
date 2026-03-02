def _normalize_host(host: str) -> str:
    """Normalize AWS S3 regional endpoints to standard format.

    Converts s3-{region}.amazonaws.com to s3.{region}.amazonaws.com
    to prevent Minio client from incorrectly transforming URLs.

    Args:
        host: The original host endpoint

    Returns:
        Normalized host endpoint
    """
    # Fix AWS regional endpoints: s3-region.amazonaws.com -> s3.region.amazonaws.com
    if host.startswith('s3-') and '.amazonaws.com' in host:
        return host.replace('s3-', 's3.', 1)
    return host