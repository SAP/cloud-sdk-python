from typing import Optional
from sap_cloud_sdk.dms._models import DMSCredentials
from sap_cloud_sdk.dms.client import DMSClient
from sap_cloud_sdk.dms.config import BindingData, load_sdm_config_from_env_or_mount


def create_client(
    *,
    instance: Optional[str] = None,
    config: Optional[BindingData] = None,
    dms_cred: Optional[DMSCredentials] = None
):
    
    if config is not None and dms_cred is not None:
        raise ValueError("Cannot provide both config and dms_cred. Please choose one.")
    if config is not None:
        config.validate()
        return DMSClient(config.to_credentials())
    if dms_cred is not None:
        return DMSClient(dms_cred)
    if instance is not None:
        return DMSClient(load_sdm_config_from_env_or_mount(instance))
    
    raise ValueError("No configuration provided. Please provide either instance name, config, or dms_cred.")