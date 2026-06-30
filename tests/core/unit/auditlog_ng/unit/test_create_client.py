"""Tests for create_client factory function."""

import pytest
from unittest.mock import patch, Mock, MagicMock

from sap_cloud_sdk.core.auditlog_ng import create_client, AuditClient
from sap_cloud_sdk.core.auditlog_ng.config import AuditLogNGConfig
from sap_cloud_sdk.core.auditlog_ng.exceptions import ClientCreationError
from sap_cloud_sdk.core.telemetry import Module, Operation


class TestCreateClient:

    @patch("sap_cloud_sdk.core.auditlog_ng.client._create_log_exporter")
    @patch("sap_cloud_sdk.core.auditlog_ng.client.LoggerProvider")
    def test_create_client_with_config(self, mock_provider_cls, mock_exporter_fn):
        mock_provider = Mock()
        mock_provider.get_logger.return_value = Mock()
        mock_provider_cls.return_value = mock_provider

        config = AuditLogNGConfig(
            endpoint="localhost:4317",
            deployment_id="dep-1",
            namespace="ns-1",
            insecure=True,
        )

        client = create_client(config=config)

        assert isinstance(client, AuditClient)

    @patch("sap_cloud_sdk.core.auditlog_ng.client._create_log_exporter")
    @patch("sap_cloud_sdk.core.auditlog_ng.client.LoggerProvider")
    def test_create_client_with_keyword_args(self, mock_provider_cls, mock_exporter_fn):
        mock_provider = Mock()
        mock_provider.get_logger.return_value = Mock()
        mock_provider_cls.return_value = mock_provider

        client = create_client(
            endpoint="localhost:4317",
            deployment_id="dep-1",
            namespace="ns-1",
            insecure=True,
        )

        assert isinstance(client, AuditClient)

    def test_create_client_missing_endpoint_raises(self):
        with pytest.raises(ValueError, match="endpoint, deployment_id, and namespace are required"):
            create_client(deployment_id="dep-1", namespace="ns-1")

    @pytest.mark.parametrize(
        ("kwargs", "match"),
        [
            (
                {"deployment_id": "dep-1", "namespace": "ns-1"},
                "endpoint, deployment_id, and namespace are required",
            ),
            (
                {
                    "endpoint": "localhost:4317",
                    "deployment_id": "bad value",
                    "namespace": "ns-1",
                },
                "deployment_id",
            ),
        ],
    )
    def test_create_client_config_errors_record_error_metric(self, kwargs, match):
        with patch(
            "sap_cloud_sdk.core.auditlog_ng._record_error_metric"
        ) as mock_error_metric:
            with pytest.raises(
                ValueError,
                match=match,
            ):
                create_client(
                    _telemetry_source=Module.DMS,
                    **kwargs,
                )

        mock_error_metric.assert_called_once_with(
            Module.AUDITLOG_NG,
            Module.DMS,
            Operation.AUDITLOG_CREATE_CLIENT,
        )

    def test_create_client_missing_deployment_id_raises(self):
        with pytest.raises(ValueError, match="endpoint, deployment_id, and namespace are required"):
            create_client(endpoint="localhost:4317", namespace="ns-1")

    def test_create_client_missing_namespace_raises(self):
        with pytest.raises(ValueError, match="endpoint, deployment_id, and namespace are required"):
            create_client(endpoint="localhost:4317", deployment_id="dep-1")

    def test_create_client_no_args_raises(self):
        with pytest.raises(ValueError, match="endpoint, deployment_id, and namespace are required"):
            create_client()

    def test_create_client_invalid_deployment_id_raises(self):
        with pytest.raises(ValueError, match="deployment_id"):
            create_client(
                endpoint="localhost:4317",
                deployment_id="bad value",
                namespace="ns-1",
            )

    @patch("sap_cloud_sdk.core.auditlog_ng.client._create_log_exporter")
    @patch("sap_cloud_sdk.core.auditlog_ng.client.LoggerProvider")
    @patch(
        "sap_cloud_sdk.core.auditlog_ng._get_config_from_destination",
        return_value={},
    )
    def test_create_client_unexpected_exception_wraps_in_client_creation_error(
        self, _mock_dest, mock_provider_cls, mock_exporter_fn
    ):
        mock_provider_cls.side_effect = RuntimeError("Unexpected failure")

        with patch(
            "sap_cloud_sdk.core.telemetry.metrics_decorator.record_error_metric"
        ) as mock_error_metric:
            with patch(
                "sap_cloud_sdk.core.telemetry.metrics_decorator.record_request_metric"
            ) as mock_request_metric:
                with pytest.raises(
                    ClientCreationError, match="Failed to create audit log NG client"
                ):
                    create_client(
                        endpoint="localhost:4317",
                        deployment_id="dep-1",
                        namespace="ns-1",
                        insecure=True,
                        _telemetry_source=Module.DMS,
                    )

        mock_error_metric.assert_called_once_with(
            Module.AUDITLOG_NG,
            Module.DMS,
            Operation.AUDITLOG_CREATE_CLIENT,
            False,
            )
        mock_request_metric.assert_not_called()

    @patch("sap_cloud_sdk.core.auditlog_ng.client._create_log_exporter")
    @patch("sap_cloud_sdk.core.auditlog_ng.client.LoggerProvider")
    def test_config_keyword_args_are_forwarded(self, mock_provider_cls, mock_exporter_fn):
        mock_provider = Mock()
        mock_provider.get_logger.return_value = Mock()
        mock_provider_cls.return_value = mock_provider

        client = create_client(
            endpoint="audit.example.com:443",
            deployment_id="dep-1",
            namespace="ns-1",
            service_name="my-svc",
            batch=True,
            compression=False,
            insecure=True,
        )

        assert client._config.service_name == "my-svc"
        assert client._config.batch is True
        assert client._config.compression is False

    @patch("sap_cloud_sdk.core.auditlog_ng.client._create_log_exporter")
    @patch("sap_cloud_sdk.core.auditlog_ng.client.LoggerProvider")
    def test_create_client_records_metric_once_with_source(
        self, mock_provider_cls, mock_exporter_fn
    ):
        mock_provider = Mock()
        mock_provider.get_logger.return_value = Mock()
        mock_provider_cls.return_value = mock_provider

        config = AuditLogNGConfig(
            endpoint="localhost:4317",
            deployment_id="dep-1",
            namespace="ns-1",
            insecure=True,
        )

        with patch(
            "sap_cloud_sdk.core.telemetry.metrics_decorator.record_request_metric"
        ) as mock_metric:
            create_client(config=config, _telemetry_source=Module.DMS)

        mock_metric.assert_called_once_with(
            Module.AUDITLOG_NG,
            Module.DMS,
            Operation.AUDITLOG_CREATE_CLIENT,
            False,
        )


# ---------------------------------------------------------------------------
# Destination-based resolution
# ---------------------------------------------------------------------------

def _make_mock_destination(
    url="audit.example.com:443",
    deployment_id="dep-1",
    deployment_region=None,
    namespace="ns-1",
):
    """Return a mock Destination with the given property values."""
    props = {}
    if deployment_id is not None:
        props["deploymentId"] = deployment_id
    if deployment_region is not None:
        props["deploymentRegion"] = deployment_region
    if namespace is not None:
        props["namespace"] = namespace

    dest = MagicMock()
    dest.url = url
    dest.properties = props
    return dest


@patch("sap_cloud_sdk.core.auditlog_ng.client._create_log_exporter")
@patch("sap_cloud_sdk.core.auditlog_ng.client.LoggerProvider")
class TestCreateClientFromDestination:

    # ------------------------------------------------------------------
    # Happy path — destination resolution is always attempted
    # ------------------------------------------------------------------

    def test_destination_triggered_by_tenant(
        self, mock_provider_cls, mock_exporter_fn
    ):
        """_get_config_from_destination is called only when tenant is provided.

        With tenant set and defaults destination_name='AuditLogV3_Destination' and
        destination_instance='default', create_client() resolves config from the destination.
        """
        mock_provider = Mock()
        mock_provider.get_logger.return_value = Mock()
        mock_provider_cls.return_value = mock_provider

        dest = _make_mock_destination(
            url="audit.default.com:443",
            deployment_id="dep-default",
            namespace="ns-default",
        )
        dest_client = MagicMock()
        dest_client.get_destination.return_value = dest

        with patch(
            "sap_cloud_sdk.destination.create_client",
            return_value=dest_client,
        ) as mock_dest_factory:
            client = create_client(tenant="my-tenant", insecure=True)

        mock_dest_factory.assert_called_once_with(instance="default")
        dest_client.get_destination.assert_called_once()
        call_kwargs = dest_client.get_destination.call_args.kwargs
        assert call_kwargs["name"] == "AuditLogV3_Destination"
        assert call_kwargs["tenant"] == "my-tenant"
        assert isinstance(client, AuditClient)
        assert client._config.endpoint == "audit.default.com:443"
        assert client._config.deployment_id == "dep-default"
        assert client._config.namespace == "ns-default"

    def test_destination_not_triggered_without_tenant(
        self, mock_provider_cls, mock_exporter_fn
    ):
        """_get_config_from_destination is NOT called when tenant is not provided.

        Without a tenant, create_client() skips destination resolution and
        requires explicit endpoint/deployment_id/namespace.
        """
        with patch(
            "sap_cloud_sdk.core.auditlog_ng._get_config_from_destination"
        ) as mock_get_config:
            with pytest.raises(ValueError, match="endpoint, deployment_id, and namespace are required"):
                create_client(insecure=True)

        mock_get_config.assert_not_called()

    def test_destination_happy_path(self, mock_provider_cls, mock_exporter_fn):
        """Resolved destination with deploymentId sets endpoint/deployment_id/namespace."""
        mock_provider = Mock()
        mock_provider.get_logger.return_value = Mock()
        mock_provider_cls.return_value = mock_provider

        dest = _make_mock_destination(
            url="audit.example.com:443",
            deployment_id="dep-1",
            namespace="ns-1",
        )
        dest_client = MagicMock()
        dest_client.get_destination.return_value = dest

        with patch(
            "sap_cloud_sdk.destination.create_client",
            return_value=dest_client,
        ):
            client = create_client(
                tenant="my-tenant",
                destination_name="my-audit-dest",
                destination_instance="my-instance",
                fragment_name="prod",
                insecure=True,
            )

        assert isinstance(client, AuditClient)
        assert client._config.endpoint == "audit.example.com:443"
        assert client._config.deployment_id == "dep-1"
        assert client._config.namespace == "ns-1"

    def test_destination_create_client_called_with_instance(self, mock_provider_cls, mock_exporter_fn):
        """destination_instance is forwarded as instance= to _dest_create_client()."""
        mock_provider = Mock()
        mock_provider.get_logger.return_value = Mock()
        mock_provider_cls.return_value = mock_provider

        dest = _make_mock_destination()
        dest_client = MagicMock()
        dest_client.get_destination.return_value = dest

        with patch(
            "sap_cloud_sdk.destination.create_client",
            return_value=dest_client,
        ) as mock_dest_factory:
            create_client(
                tenant="my-tenant",
                destination_name="my-audit-dest",
                destination_instance="my-instance",
                fragment_name="prod",
                insecure=True,
            )

        mock_dest_factory.assert_called_once_with(instance="my-instance")

    def test_destination_fragment_name_forwarded(self, mock_provider_cls, mock_exporter_fn):
        """fragment_name is always wrapped in ConsumptionOptions and forwarded to get_destination."""
        mock_provider = Mock()
        mock_provider.get_logger.return_value = Mock()
        mock_provider_cls.return_value = mock_provider

        dest = _make_mock_destination()
        dest_client = MagicMock()
        dest_client.get_destination.return_value = dest

        with patch(
            "sap_cloud_sdk.destination.create_client",
            return_value=dest_client,
        ):
            create_client(
                tenant="my-tenant",
                destination_name="my-audit-dest",
                destination_instance="my-instance",
                fragment_name="prod",
                insecure=True,
            )

        from sap_cloud_sdk.destination import ConsumptionLevel

        call_kwargs = dest_client.get_destination.call_args.kwargs
        options = call_kwargs.get("options")
        assert options is not None
        assert options.fragment_name == "prod"
        assert options.fragment_level == ConsumptionLevel.SUBACCOUNT

    def test_destination_name_alone_enters_destination_path(
        self, mock_provider_cls, mock_exporter_fn
    ):
        """tenant + destination_name enters the destination path (destination_instance
        defaults to 'default'); the explicit-args guard is NOT raised."""
        mock_provider = Mock()
        mock_provider.get_logger.return_value = Mock()
        mock_provider_cls.return_value = mock_provider

        dest = _make_mock_destination()
        dest_client = MagicMock()
        dest_client.get_destination.return_value = dest

        with patch(
            "sap_cloud_sdk.destination.create_client",
            return_value=dest_client,
        ) as mock_dest_factory:
            client = create_client(
                tenant="my-tenant",
                destination_name="my-audit-dest",
                insecure=True,
            )

        mock_dest_factory.assert_called_once_with(instance="default")
        assert isinstance(client, AuditClient)

    def test_destination_name_without_fragment_uses_destination_path(
        self, mock_provider_cls, mock_exporter_fn
    ):
        """tenant + destination_name + destination_instance without fragment_name still enters the
        destination path; get_destination is called with options=None."""
        mock_provider = Mock()
        mock_provider.get_logger.return_value = Mock()
        mock_provider_cls.return_value = mock_provider

        dest = _make_mock_destination()
        dest_client = MagicMock()
        dest_client.get_destination.return_value = dest

        with patch(
            "sap_cloud_sdk.destination.create_client",
            return_value=dest_client,
        ):
            client = create_client(
                tenant="my-tenant",
                destination_name="my-audit-dest",
                destination_instance="inst",
                insecure=True,
            )

        assert isinstance(client, AuditClient)
        call_kwargs = dest_client.get_destination.call_args.kwargs
        assert call_kwargs.get("options") is None

    def test_destination_name_without_instance_uses_default_instance(
        self, mock_provider_cls, mock_exporter_fn
    ):
        """tenant + destination_name with fragment_name but no destination_instance enters the
        destination path, calling _dest_create_client with instance='default'."""
        mock_provider = Mock()
        mock_provider.get_logger.return_value = Mock()
        mock_provider_cls.return_value = mock_provider

        dest = _make_mock_destination()
        dest_client = MagicMock()
        dest_client.get_destination.return_value = dest

        with patch(
            "sap_cloud_sdk.destination.create_client",
            return_value=dest_client,
        ) as mock_dest_factory:
            client = create_client(
                tenant="my-tenant",
                destination_name="my-audit-dest",
                fragment_name="prod",
                insecure=True,
            )

        mock_dest_factory.assert_called_once_with(instance="default")
        assert isinstance(client, AuditClient)

    # ------------------------------------------------------------------
    # deploymentRegion fallback
    # ------------------------------------------------------------------

    def test_fallback_deployment_region_when_deployment_id_missing(
        self, mock_provider_cls, mock_exporter_fn
    ):
        """When deploymentId is absent, deploymentRegion is used as deployment_id."""
        mock_provider = Mock()
        mock_provider.get_logger.return_value = Mock()
        mock_provider_cls.return_value = mock_provider

        dest = _make_mock_destination(
            deployment_id=None,
            deployment_region="eu10",
        )
        dest_client = MagicMock()
        dest_client.get_destination.return_value = dest

        with patch(
            "sap_cloud_sdk.destination.create_client",
            return_value=dest_client,
        ):
            client = create_client(
                tenant="my-tenant",
                destination_name="my-audit-dest",
                destination_instance="my-instance",
                fragment_name="prod",
                insecure=True,
            )

        assert client._config.deployment_id == "eu10"

    def test_fallback_deployment_region_when_deployment_id_empty(
        self, mock_provider_cls, mock_exporter_fn
    ):
        """When deploymentId is an empty string, deploymentRegion is used instead."""
        mock_provider = Mock()
        mock_provider.get_logger.return_value = Mock()
        mock_provider_cls.return_value = mock_provider

        dest = _make_mock_destination(
            deployment_id="",
            deployment_region="eu20",
        )
        dest_client = MagicMock()
        dest_client.get_destination.return_value = dest

        with patch(
            "sap_cloud_sdk.destination.create_client",
            return_value=dest_client,
        ):
            client = create_client(
                tenant="my-tenant",
                destination_name="my-audit-dest",
                destination_instance="my-instance",
                fragment_name="prod",
                insecure=True,
            )

        assert client._config.deployment_id == "eu20"

    # ------------------------------------------------------------------
    # Missing required destination properties
    # ------------------------------------------------------------------

    def test_missing_both_deployment_props_raises(
        self, mock_provider_cls, mock_exporter_fn
    ):
        """Raises ValueError when neither deploymentId nor deploymentRegion is present."""
        dest = _make_mock_destination(deployment_id=None, deployment_region=None)
        dest_client = MagicMock()
        dest_client.get_destination.return_value = dest

        with patch(
            "sap_cloud_sdk.destination.create_client",
            return_value=dest_client,
        ):
            with pytest.raises(ValueError, match="deploymentId.*deploymentRegion"):
                create_client(
                    tenant="my-tenant",
                    destination_name="my-audit-dest",
                    destination_instance="my-instance",
                    fragment_name="prod",
                )

    def test_missing_namespace_raises(self, mock_provider_cls, mock_exporter_fn):
        """Raises ValueError when the namespace property is absent."""
        dest = _make_mock_destination(namespace=None)
        dest_client = MagicMock()
        dest_client.get_destination.return_value = dest

        with patch(
            "sap_cloud_sdk.destination.create_client",
            return_value=dest_client,
        ):
            with pytest.raises(ValueError, match="namespace"):
                create_client(
                    tenant="my-tenant",
                    destination_name="my-audit-dest",
                    destination_instance="my-instance",
                    fragment_name="prod",
                )

    def test_missing_url_propagates_as_endpoint_required(self, mock_provider_cls, mock_exporter_fn):
        """When the destination URL is None, AuditLogNGConfig raises 'endpoint is required'."""
        dest = _make_mock_destination(url=None)
        dest_client = MagicMock()
        dest_client.get_destination.return_value = dest

        with patch(
            "sap_cloud_sdk.destination.create_client",
            return_value=dest_client,
        ):
            with pytest.raises(ValueError, match="endpoint is required"):
                create_client(
                    tenant="my-tenant",
                    destination_name="my-audit-dest",
                    destination_instance="my-instance",
                    fragment_name="prod",
                )

    def test_destination_not_found_raises(self, mock_provider_cls, mock_exporter_fn):
        """Raises ValueError when get_destination returns None and no explicit args are given.

        When tenant is set but the destination is not found, _get_config_from_destination
        returns {} and AuditLogNGConfig is called with endpoint=None, raising 'endpoint is required'.
        """
        dest_client = MagicMock()
        dest_client.get_destination.return_value = None

        with patch(
            "sap_cloud_sdk.destination.create_client",
            return_value=dest_client,
        ):
            with pytest.raises(ValueError, match="endpoint is required"):
                create_client(
                    tenant="my-tenant",
                    destination_name="missing-dest",
                    destination_instance="my-instance",
                    fragment_name="prod",
                )

    # ------------------------------------------------------------------
    # No-destination path is fully preserved (regression)
    # ------------------------------------------------------------------

    def test_no_destination_explicit_args_still_works(
        self, mock_provider_cls, mock_exporter_fn
    ):
        """Existing keyword-arg path is unaffected when destination resolution returns empty dict."""
        mock_provider = Mock()
        mock_provider.get_logger.return_value = Mock()
        mock_provider_cls.return_value = mock_provider

        with patch(
            "sap_cloud_sdk.core.auditlog_ng._get_config_from_destination",
            return_value={},
        ):
            client = create_client(
                endpoint="localhost:4317",
                deployment_id="dep-1",
                namespace="ns-1",
                insecure=True,
            )

        assert isinstance(client, AuditClient)
        assert client._config.endpoint == "localhost:4317"

    def test_no_destination_config_object_still_works(
        self, mock_provider_cls, mock_exporter_fn
    ):
        """Existing config-object path is unaffected; destination resolution is skipped when config is given."""
        mock_provider = Mock()
        mock_provider.get_logger.return_value = Mock()
        mock_provider_cls.return_value = mock_provider

        config = AuditLogNGConfig(
            endpoint="localhost:4317",
            deployment_id="dep-1",
            namespace="ns-1",
            insecure=True,
        )

        client = create_client(config=config)

        assert isinstance(client, AuditClient)
