"""Tests for configure_extension_logging."""

import logging

from sap_cloud_sdk.extensibility._logging import configure_extension_logging


class TestConfigureExtensionLogging:
    def test_attaches_filter_to_handlers(self):
        handler = logging.StreamHandler()
        root = logging.getLogger()
        original_handlers = root.handlers[:]
        root.handlers = [handler]
        try:
            configure_extension_logging()
            from sap_cloud_sdk.core.telemetry import ExtensionContextLogFilter

            assert any(
                isinstance(f, ExtensionContextLogFilter) for f in handler.filters
            )
        finally:
            root.handlers = original_handlers

    def test_idempotent_second_call(self):
        handler = logging.StreamHandler()
        root = logging.getLogger()
        original_handlers = root.handlers[:]
        root.handlers = [handler]
        try:
            configure_extension_logging()
            configure_extension_logging()
            from sap_cloud_sdk.core.telemetry import ExtensionContextLogFilter

            count = sum(
                1 for f in handler.filters if isinstance(f, ExtensionContextLogFilter)
            )
            assert count == 1
        finally:
            root.handlers = original_handlers

    def test_no_handlers_does_not_raise(self):
        root = logging.getLogger()
        original_handlers = root.handlers[:]
        root.handlers = []
        try:
            configure_extension_logging()
        finally:
            root.handlers = original_handlers

    def test_multiple_handlers_each_get_filter(self):
        handler1 = logging.StreamHandler()
        handler2 = logging.StreamHandler()
        root = logging.getLogger()
        original_handlers = root.handlers[:]
        root.handlers = [handler1, handler2]
        try:
            configure_extension_logging()
            from sap_cloud_sdk.core.telemetry import ExtensionContextLogFilter

            for h in [handler1, handler2]:
                assert any(isinstance(f, ExtensionContextLogFilter) for f in h.filters)
        finally:
            root.handlers = original_handlers
