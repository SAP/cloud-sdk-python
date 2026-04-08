"""SAP Cloud SDK for Python - Document Management Service (DMS) module

The create_client() function loads credentials from mounts/env vars and points
to an instance in the cloud.

Usage:
    from sap_cloud_sdk.dms import create_client

    # Recommended: use the factory which configures OAuth/HTTP from environment
    client = create_client()

    # Or specify a named instance
    client = create_client(instance="my-sdm-instance")

    # List all onboarded repositories
    repos = client.get_all_repositories()

    # Create a folder
    folder = client.create_folder(repo.id, root_folder_id, "MyFolder")

    # Upload a document
    with open("file.pdf", "rb") as f:
        doc = client.create_document(
            repo.id, folder.object_id, "file.pdf", f, mime_type="application/pdf"
        )
"""

from typing import Optional

from sap_cloud_sdk.core.telemetry import Module
from sap_cloud_sdk.dms.model import DMSCredentials
from sap_cloud_sdk.dms.client import DMSClient
from sap_cloud_sdk.dms.config import load_sdm_config_from_env_or_mount
from sap_cloud_sdk.dms.exceptions import DMSError


def create_client(
    *,
    instance: Optional[str] = None,
    dms_cred: Optional[DMSCredentials] = None,
    _telemetry_source: Optional[Module] = None,
):
    try:
        credentials = dms_cred or load_sdm_config_from_env_or_mount(instance)
        client = DMSClient(credentials)
        client._telemetry_source = _telemetry_source
        return client
    except Exception as e:
        raise DMSError(f"Failed to create DMS client: {e}") from e


__all__ = ["create_client"]
