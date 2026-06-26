"""Sync + async API for the ADMS Job service (zip downloads, GDPR deletes)."""

from __future__ import annotations

from sap_cloud_sdk.core.odata._entity_key import EntityKey
from sap_cloud_sdk.core.odata._transport import ODataHttpTransport
from sap_cloud_sdk.core.odata._async_transport import AsyncODataHttpTransport
from sap_cloud_sdk.adms._models import (
    DeleteUserDataJobParameters,
    JobOutput,
    JobType,
    ZipDownloadJobParameters,
)
from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics


class _JobApi:
    """Job operations for the ADMS module.

    Access via :attr:`AdmsClient.jobs`.
    """

    def __init__(
        self, http: ODataHttpTransport, admin_http: ODataHttpTransport
    ) -> None:
        self._http = http
        self._admin_http = admin_http

    @record_metrics(Module.ADMS, Operation.ADMS_JOBS_START_ZIP_DOWNLOAD)
    def start_zip_download(self, params: ZipDownloadJobParameters) -> JobOutput:
        """Start a ``ZIP_DOWNLOAD`` job via DocumentService.

        Args:
            params: ZIP download parameters.

        Returns:
            :class:`~sap_cloud_sdk.adms._models.JobOutput` with the ``job_id``.
        """
        payload = {
            "JobInput": {
                "JobType": JobType.ZIP_DOWNLOAD.value,
                "JobParameters": params.to_odata_dict(),
            }
        }
        return JobOutput.from_dict(self._http.post("StartJob", json=payload))

    @record_metrics(Module.ADMS, Operation.ADMS_JOBS_START_DELETE_USER_DATA)
    def start_delete_user_data(self, params: DeleteUserDataJobParameters) -> JobOutput:
        """Start a ``DELETE_USER_DATA`` job via AdminService (GDPR erasure).

        Args:
            params: User ID to erase.

        Returns:
            :class:`~sap_cloud_sdk.adms._models.JobOutput` with ``job_id``.
        """
        payload = {
            "JobInput": {
                "JobType": JobType.DELETE_USER_DATA.value,
                "JobParameters": params.to_odata_dict(),
            }
        }
        return JobOutput.from_dict(self._admin_http.post("StartJob", json=payload))

    @record_metrics(Module.ADMS, Operation.ADMS_JOBS_GET_STATUS)
    def get_status(
        self,
        job_id: str,
        *,
        use_admin_service: bool = False,
    ) -> JobOutput:
        """Poll the status of a running job.

        Args:
            job_id: The ``job_id`` from :meth:`start_zip_download` or
                :meth:`start_delete_user_data`.
            use_admin_service: Set ``True`` when polling a ``DELETE_USER_DATA`` job.

        Returns:
            Current :class:`~sap_cloud_sdk.adms._models.JobOutput`.
        """
        transport = self._admin_http if use_admin_service else self._http
        return JobOutput.from_dict(
            transport.get(str(EntityKey("JobStatus", JobID=job_id)))
        )


class _AsyncJobApi:
    """Async version of :class:`_JobApi`.

    Access via :attr:`AsyncAdmsClient.jobs`.
    """

    def __init__(
        self, http: AsyncODataHttpTransport, admin_http: AsyncODataHttpTransport
    ) -> None:
        self._http = http
        self._admin_http = admin_http

    @record_metrics(Module.ADMS, Operation.ADMS_JOBS_START_ZIP_DOWNLOAD)
    async def start_zip_download(self, params: ZipDownloadJobParameters) -> JobOutput:
        """Start a ``ZIP_DOWNLOAD`` job (async)."""
        payload = {
            "JobInput": {
                "JobType": JobType.ZIP_DOWNLOAD.value,
                "JobParameters": params.to_odata_dict(),
            }
        }
        return JobOutput.from_dict(await self._http.post("StartJob", json=payload))

    @record_metrics(Module.ADMS, Operation.ADMS_JOBS_START_DELETE_USER_DATA)
    async def start_delete_user_data(
        self, params: DeleteUserDataJobParameters
    ) -> JobOutput:
        """Start a ``DELETE_USER_DATA`` job via AdminService (async)."""
        payload = {
            "JobInput": {
                "JobType": JobType.DELETE_USER_DATA.value,
                "JobParameters": params.to_odata_dict(),
            }
        }
        return JobOutput.from_dict(
            await self._admin_http.post("StartJob", json=payload)
        )

    @record_metrics(Module.ADMS, Operation.ADMS_JOBS_GET_STATUS)
    async def get_status(
        self,
        job_id: str,
        *,
        use_admin_service: bool = False,
    ) -> JobOutput:
        """Poll the status of a running job (async)."""
        transport = self._admin_http if use_admin_service else self._http
        return JobOutput.from_dict(
            await transport.get(str(EntityKey("JobStatus", JobID=job_id)))
        )
