"""Sync + async API for the ADMS Job service (zip downloads, GDPR deletes)."""

from __future__ import annotations

from sap_cloud_sdk.adms._http import (
    AdmsHttp,
    AsyncAdmsHttp,
    build_job_status_key_path,
)
from sap_cloud_sdk.adms._models import (
    DeleteUserDataJobParameters,
    JobOutput,
    JobType,
    ZipDownloadJobParameters,
)
from sap_cloud_sdk.adms.config import _ADMIN_SERVICE_PATH, _SERVICE_PATH
from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics


class _JobApi:
    """Async job operations for the ADMS module.

    Access via :attr:`AdmsClient.jobs`.
    """

    def __init__(self, http: AdmsHttp) -> None:
        self._http = http

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
        resp = self._http.post("StartJob", json=payload, service_base=_SERVICE_PATH)
        return JobOutput.from_dict(resp.json())

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
        resp = self._http.post(
            "StartJob", json=payload, service_base=_ADMIN_SERVICE_PATH
        )
        return JobOutput.from_dict(resp.json())

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
        service = _ADMIN_SERVICE_PATH if use_admin_service else _SERVICE_PATH
        path = build_job_status_key_path(job_id)
        resp = self._http.get(path, service_base=service)
        return JobOutput.from_dict(resp.json())


class _AsyncJobApi:
    """Async version of :class:`_JobApi`.

    Access via :attr:`AsyncAdmsClient.jobs`.
    """

    def __init__(self, http: AsyncAdmsHttp) -> None:
        self._http = http

    @record_metrics(Module.ADMS, Operation.ADMS_JOBS_START_ZIP_DOWNLOAD)
    async def start_zip_download(self, params: ZipDownloadJobParameters) -> JobOutput:
        """Start a ``ZIP_DOWNLOAD`` job (async)."""
        payload = {
            "JobInput": {
                "JobType": JobType.ZIP_DOWNLOAD.value,
                "JobParameters": params.to_odata_dict(),
            }
        }
        resp = await self._http.post(
            "StartJob", json=payload, service_base=_SERVICE_PATH
        )
        return JobOutput.from_dict(resp.json())

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
        resp = await self._http.post(
            "StartJob", json=payload, service_base=_ADMIN_SERVICE_PATH
        )
        return JobOutput.from_dict(resp.json())

    @record_metrics(Module.ADMS, Operation.ADMS_JOBS_GET_STATUS)
    async def get_status(
        self,
        job_id: str,
        *,
        use_admin_service: bool = False,
    ) -> JobOutput:
        """Poll the status of a running job (async).

        Args:
            job_id: The ``job_id`` from :meth:`start_zip_download` or
                :meth:`start_delete_user_data`.
            use_admin_service: Set ``True`` when polling a ``DELETE_USER_DATA`` job.

        Returns:
            Current :class:`~sap_cloud_sdk.adms._models.JobOutput`.
        """
        service = _ADMIN_SERVICE_PATH if use_admin_service else _SERVICE_PATH
        path = build_job_status_key_path(job_id)
        resp = await self._http.get(path, service_base=service)
        return JobOutput.from_dict(resp.json())
