"""Pytest configuration for dpi_ng tests."""

from __future__ import annotations

# pydantic.root_model must be in sys.modules before traceloop.sdk is imported,
# otherwise traceloop's generic RootModel subclasses raise KeyError at collection time.
import pydantic.root_model  # noqa: F401
