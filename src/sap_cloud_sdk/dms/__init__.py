from typing import Optional
from sap_cloud_sdk.dms.model.model import DMSCredentials
from sap_cloud_sdk.dms.client import DMSClient
from sap_cloud_sdk.dms.config import load_sdm_config_from_env_or_mount


def create_client(
    *,
    instance: Optional[str] = None,
    dms_cred: Optional[DMSCredentials] = None
):
    if dms_cred is not None:
        return DMSClient(dms_cred)
    if instance is not None:
        return DMSClient(load_sdm_config_from_env_or_mount(instance))
    
    raise ValueError("No configuration provided. Please provide either instance name, config, or dms_cred.")

__all__ = ["create_client"]