"""SAP Print Service client implementation."""

from __future__ import annotations

import logging
from typing import IO, Optional, Union

from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics
from sap_cloud_sdk.print._http import PrintHttp
from sap_cloud_sdk.print.exceptions import HttpError, PrintOperationError
from sap_cloud_sdk.print._models import PrintProfile, PrintQueue, PrintTask

_QUEUES_PATH = "qm/api/v1/rest/queues"
_DOCUMENTS_PATH = "dm/api/v1/rest/print-documents"
_TASKS_PATH = "qm/api/v1/rest/print-tasks"

_IF_NONE_MATCH = {"If-None-Match": "*"}

logger = logging.getLogger(__name__)


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
        self, http: PrintHttp, _telemetry_source: Optional[Module] = None
    ) -> None:
        self._http = http
        self._telemetry_source = _telemetry_source

    @record_metrics(Module.PRINT, Operation.PRINT_LIST_QUEUES)
    def list_queues(self) -> list[PrintQueue]:
        """Retrieve all print queues available in the tenant.

        Returns:
            List of PrintQueue objects.

        Raises:
            PrintOperationError: If the request fails or the response cannot be parsed.
        """
        try:
            resp = self._http.get(_QUEUES_PATH)
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
            self._http.put(
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
            resp = self._http.get(f"{_QUEUES_PATH}/{qname}/profiles")
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
            resp = self._http.post(
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
            task.username = self._http.get_username()
        try:
            self._http.put(
                f"{_TASKS_PATH}/{task.item_id}",
                json=task.to_body(),
                headers=_IF_NONE_MATCH,
            )
        except HttpError as e:
            logger.error("failed to create print task: %s", e)
            raise PrintOperationError(f"failed to create print task: {e}") from e
