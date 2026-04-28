"""Unit tests for the Temporal client module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sap_cloud_sdk.temporal.client import TemporalClient, create_client, create_worker
from sap_cloud_sdk.temporal.config import TemporalConfig
from sap_cloud_sdk.temporal.exceptions import ClientCreationError, WorkerCreationError


@pytest.fixture
def local_dev_config():
    return TemporalConfig(
        target="localhost:7233",
        namespace="default",
        is_local_dev=True,
    )


@pytest.fixture
def mock_inner_client():
    client = MagicMock()
    client.identity = "test-identity"
    return client


@pytest.fixture
def temporal_client(mock_inner_client, local_dev_config):
    return TemporalClient(mock_inner_client, local_dev_config)


class TestTemporalClientProperties:
    def test_inner_returns_underlying_client(self, temporal_client, mock_inner_client):
        assert temporal_client.inner is mock_inner_client

    def test_namespace_from_config(self, temporal_client):
        assert temporal_client.namespace == "default"

    def test_identity_from_inner(self, temporal_client):
        assert temporal_client.identity == "test-identity"


class TestCreateClient:
    @pytest.mark.asyncio
    async def test_local_dev_connects_without_tls(self, monkeypatch):
        monkeypatch.setenv("APPFND_LOCALDEV_TEMPORAL", "true")
        mock_client = MagicMock()

        with patch(
            "sap_cloud_sdk.temporal.client.Client.connect",
            new_callable=AsyncMock,
            return_value=mock_client,
        ) as mock_connect:
            client = await create_client()

        assert isinstance(client, TemporalClient)
        call_kwargs = mock_connect.call_args.kwargs
        assert call_kwargs["tls"] is False
        assert call_kwargs["target_host"] == "localhost:7233"

    @pytest.mark.asyncio
    async def test_connection_error_raises_client_creation_error(self, monkeypatch):
        monkeypatch.setenv("APPFND_LOCALDEV_TEMPORAL", "true")

        with patch(
            "sap_cloud_sdk.temporal.client.Client.connect",
            new_callable=AsyncMock,
            side_effect=OSError("connection refused"),
        ):
            with pytest.raises(ClientCreationError, match="connection refused"):
                await create_client()

    @pytest.mark.asyncio
    async def test_configuration_error_wrapped(self, monkeypatch):
        monkeypatch.delenv("APPFND_LOCALDEV_TEMPORAL", raising=False)
        monkeypatch.delenv("TEMPORAL_CALL_URL", raising=False)

        with pytest.raises(ClientCreationError):
            await create_client()


class TestCreateWorker:
    def test_create_worker_success(self, temporal_client):
        mock_workflow = MagicMock()
        mock_activity = MagicMock()

        with patch("sap_cloud_sdk.temporal.client.Worker") as mock_worker_cls:
            mock_worker_cls.return_value = MagicMock()
            worker = create_worker(
                temporal_client,
                task_queue="test-queue",
                workflows=[mock_workflow],
                activities=[mock_activity],
            )

        assert worker is mock_worker_cls.return_value

    def test_create_worker_no_workflows_or_activities_raises(self, temporal_client):
        with pytest.raises(WorkerCreationError, match="At least one"):
            create_worker(temporal_client, task_queue="test-queue")

    def test_create_worker_passes_inner_client(self, temporal_client, mock_inner_client):
        with patch("sap_cloud_sdk.temporal.client.Worker") as mock_worker_cls:
            mock_worker_cls.return_value = MagicMock()
            create_worker(
                temporal_client,
                task_queue="test-queue",
                workflows=[MagicMock()],
            )
        call_kwargs = mock_worker_cls.call_args.kwargs
        assert call_kwargs["client"] is mock_inner_client

    def test_create_worker_construction_error_raises(self, temporal_client):
        with patch(
            "sap_cloud_sdk.temporal.client.Worker",
            side_effect=Exception("bad config"),
        ):
            with pytest.raises(WorkerCreationError, match="bad config"):
                create_worker(
                    temporal_client,
                    task_queue="test-queue",
                    workflows=[MagicMock()],
                )
