"""SAP Print Service client implementation."""

from __future__ import annotations

import base64
import json
import logging
from typing import IO, Any, Callable, Dict, Optional, Union

from oauthlib.oauth2 import BackendApplicationClient
from requests.exceptions import RequestException
from requests_oauthlib import OAuth2Session

from sap_cloud_sdk.core.protocol.http import HttpClient
from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics
from sap_cloud_sdk.print.config import PrintConfig
from sap_cloud_sdk.print.exceptions import HttpError, PrintOperationError
from sap_cloud_sdk.print._models import PrintProfile, PrintQueue, PrintTask

_QUEUES_PATH = "/qm/api/v1/rest/queues"
_DOCUMENTS_PATH = "/dm/api/v1/rest/print-documents"
_TASKS_PATH = "/qm/api/v1/rest/print-tasks"

_IF_NONE_MATCH = {"If-None-Match": "*"}

logger = logging.getLogger(__name__)


class TokenProvider:
    """Provides OAuth2 access tokens via client credentials flow.

    Accepts either a fixed :class:`PrintConfig` or a config factory (any callable
    returning ``PrintConfig`` with an optional ``has_changed() -> bool`` method).
    When a factory is supplied, credentials are re-read on every token fetch and
    the factory's ``has_changed()`` method is checked before serving a cached token
    so that rotated secrets are picked up proactively.
    """

    def __init__(self, config: PrintConfig | Callable[[], PrintConfig]) -> None:
        if callable(config) and not isinstance(config, PrintConfig):
            self._config_factory: Callable[[], PrintConfig] = config
            self._config = config()
        else:
            self._config_factory = lambda: config  # type: ignore[arg-type]
            self._config = config  # type: ignore[assignment]
        client = BackendApplicationClient(client_id=self._config.client_id)
        self._session = OAuth2Session(client=client)
        self._cached_token: Optional[str] = None

    def _refresh_if_rotated(self) -> None:
        has_changed = getattr(self._config_factory, "has_changed", None)
        if callable(has_changed) and has_changed():
            self._config = self._config_factory()
            self._cached_token = None
            client = BackendApplicationClient(client_id=self._config.client_id)
            self._session = OAuth2Session(client=client)

    def get_token(self) -> str:
        """Return a valid bearer token for the Print Service.

        Returns:
            A non-empty OAuth2 access token string.

        Raises:
            HttpError: If the token response is missing an access_token or
                token acquisition fails.
        """
        self._refresh_if_rotated()

        try:
            token: Dict[str, Any] = self._session.fetch_token(
                token_url=self._config.token_url,
                client_id=self._config.client_id,
                client_secret=self._config.client_secret,
                include_client_id=True,
            )
        except Exception as e:
            logger.error("failed to acquire token: %s", e)
            raise HttpError(f"failed to acquire token: {e}") from e
        access_token = token.get("access_token")
        if not access_token:
            raise HttpError("token response missing access_token")
        self._cached_token = str(access_token)
        return self._cached_token

    def resolve_username(self) -> str:
        """Resolve a username from the current access token claims.

        Returns the ``user_name`` JWT claim when present (interactive user
        flows), otherwise falls back to ``client_id`` (client-credentials /
        technical-user flows).
        """
        token = self._cached_token or self.get_token()
        try:
            payload_b64 = token.split(".")[1]
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding
            claims = json.loads(base64.urlsafe_b64decode(payload_b64))
            return str(
                claims.get("user_name")
                or claims.get("client_id")
                or self._config.client_id
            )
        except Exception:
            logger.debug("could not decode JWT claims, falling back to client_id")
            return self._config.client_id


class PrintClient:
    """Client for SAP Print Service operations.

    Note:
        Do not instantiate PrintClient directly. Use create_client() from
        sap_cloud_sdk.print instead, which handles environment detection,
        secret resolution and OAuth setup.

    Example:
        ```python
        from sap_cloud_sdk.print import create_client, PrintQueue, PrintContent, PrintTask

        client = create_client()

        # List available print queues
        queues = client.list_queues()

        # Upload a document
        with open("invoice.pdf", "rb") as f:
            document_id = client.upload_document(f)

        # Create a print task
        task = PrintTask(
            item_id=document_id,
            qname="my-queue",
            print_contents=[PrintContent(object_key=document_id, document_name="invoice.pdf")],
        )
        client.create_print_task(task)
        ```
    """

    def __init__(
        self,
        http: HttpClient,
        token_provider: TokenProvider,
        _telemetry_source: Optional[Module] = None,
    ) -> None:
        self._http = http
        self._token_provider = token_provider
        self._telemetry_source = _telemetry_source

    def get_username(self) -> str:
        """Resolve the username from the current OAuth token (or fall back to client_id)."""
        return self._token_provider.resolve_username()

    def _request(self, method: str, path: str, **kwargs):
        try:
            resp = self._http.request(method, path, **kwargs)
        except RequestException as e:
            logger.error("request failed [%s %s]: %s", method, path, e)
            raise HttpError(f"request failed: {e}") from e

        if 200 <= resp.status_code < 300:
            return resp

        text: str = ""
        try:
            text = resp.text
        except Exception:
            text = "<failed to read response body>"

        raise HttpError(
            f"HTTP {resp.status_code} for {method} {path}",
            status_code=resp.status_code,
            response_text=text,
        )

    def get(self, path: str, *, params=None, headers=None):
        return self._request("GET", path, params=params, headers=headers)

    def put(self, path: str, *, json=None, headers=None):
        return self._request("PUT", path, json=json, headers=headers)

    def post(self, path: str, *, json=None, data=None, files=None, headers=None):
        return self._request(
            "POST", path, json=json, data=data, files=files, headers=headers
        )

    @record_metrics(Module.PRINT, Operation.PRINT_LIST_QUEUES)
    def list_queues(self) -> list[PrintQueue]:
        """Retrieve all print queues available in the tenant.

        Returns:
            List of PrintQueue objects.

        Raises:
            PrintOperationError: If the request fails or the response cannot be parsed.
        """
        try:
            resp = self.get(_QUEUES_PATH)
            data = resp.json()
            return [PrintQueue.from_dict(item) for item in data]
        except HttpError as e:
            logger.error("failed to list queues: %s", e)
            raise PrintOperationError(f"failed to list queues: {e}") from e
        except Exception as e:
            logger.error("failed to parse list queues response: %s", e)
            raise PrintOperationError(
                f"failed to parse list queues response: {e}"
            ) from e

    @record_metrics(Module.PRINT, Operation.PRINT_CREATE_QUEUE)
    def create_queue(self, queue: PrintQueue) -> None:
        """Create a print queue.

        Args:
            queue: PrintQueue to create. The queue name in the body must match
                the path parameter — this is enforced automatically.

        Raises:
            PrintOperationError: If the request fails.
        """
        try:
            self.put(
                f"{_QUEUES_PATH}/{queue.qname}",
                json=queue.to_dict(),
                headers=_IF_NONE_MATCH,
            )
        except HttpError as e:
            logger.error("failed to create queue '%s': %s", queue.qname, e)
            raise PrintOperationError(
                f"failed to create queue '{queue.qname}': {e}"
            ) from e

    @record_metrics(Module.PRINT, Operation.PRINT_GET_PROFILES)
    def get_print_profiles(self, qname: str) -> list[PrintProfile]:
        """Fetch print profiles for a queue.

        Use the returned profile names when creating print tasks to send
        profile parameters to the physical printer.

        Args:
            qname: Name of the existing print queue.

        Returns:
            List of PrintProfile objects for the queue.

        Raises:
            PrintOperationError: If the request fails or the response cannot be parsed.
        """
        try:
            resp = self.get(f"{_QUEUES_PATH}/{qname}/profiles")
            data = resp.json()
            return [PrintProfile.from_dict(item) for item in data]
        except HttpError as e:
            logger.error("failed to get profiles for queue '%s': %s", qname, e)
            raise PrintOperationError(
                f"failed to get profiles for queue '{qname}': {e}"
            ) from e
        except Exception as e:
            logger.error("failed to parse get profiles response: %s", e)
            raise PrintOperationError(
                f"failed to parse get profiles response: {e}"
            ) from e

    @record_metrics(Module.PRINT, Operation.PRINT_UPLOAD_DOCUMENT)
    def upload_document(
        self,
        file: Union[IO[bytes], bytes],
        filename: str = "document",
        scan: bool = True,
    ) -> str:
        """Upload a document to Print Service cloud storage.

        The returned document ID is used as the object_key in PrintContent
        and as the item_id in PrintTask.

        Args:
            file: File-like object (opened in binary mode) or raw bytes.
            filename: Name for the uploaded file.
            scan: Whether to enable virus scanning. Defaults to True.

        Returns:
            Document ID (UUID string) to reference in create_print_task().

        Raises:
            PrintOperationError: If the upload fails.
        """
        try:
            headers = {**_IF_NONE_MATCH, "scan": str(scan).lower()}
            resp = self.post(
                _DOCUMENTS_PATH,
                files={"file": (filename, file)},
                headers=headers,
            )
            return resp.text.strip()
        except HttpError as e:
            logger.error("failed to upload document: %s", e)
            raise PrintOperationError(f"failed to upload document: {e}") from e

    @record_metrics(Module.PRINT, Operation.PRINT_CREATE_TASK)
    def create_print_task(self, task: PrintTask) -> None:
        """Send a document to a print queue.

        The task.item_id must match the object_key of the main document in
        task.print_contents. All other entries in print_contents are treated
        as attachments.

        If task.username is empty, it is resolved automatically from the
        OAuth token (``user_name`` claim) or falls back to the client ID.

        Args:
            task: PrintTask describing the print job.

        Raises:
            PrintOperationError: If the request fails.
        """
        if not task.username:
            task.username = self.get_username()
        try:
            self.put(
                f"{_TASKS_PATH}/{task.item_id}",
                json=task.to_body(),
                headers=_IF_NONE_MATCH,
            )
        except HttpError as e:
            logger.error("failed to create print task: %s", e)
            raise PrintOperationError(f"failed to create print task: {e}") from e
