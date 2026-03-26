import logging
from typing import Optional
from sap_cloud_sdk.dms.model import (
    DMSCredentials, InternalRepoRequest, Repository, UserClaim,
    UpdateRepoRequest, CreateConfigRequest, RepositoryConfig, UpdateConfigRequest,
)
from sap_cloud_sdk.dms._auth import Auth
from sap_cloud_sdk.dms._http import HttpInvoker
from sap_cloud_sdk.dms import _endpoints as endpoints
from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics

logger = logging.getLogger(__name__)


class DMSClient:
    """Client for interacting with the SAP Document Management Service Admin API."""

    def __init__(
        self,
        credentials: DMSCredentials,
        connect_timeout: Optional[int] = None,
        read_timeout: Optional[int] = None,
    ) -> None:
        auth = Auth(credentials)
        self._http: HttpInvoker = HttpInvoker(
            auth=auth,
            base_url=credentials.uri,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
        )
        logger.debug("DMSClient initialized for instance '%s'", credentials.instance_name)

    @record_metrics(Module.DMS, Operation.DMS_ONBOARD_REPOSITORY)
    def onboard_repository(
        self,
        request: InternalRepoRequest,
        tenant: Optional[str] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> Repository:
        """Onboard a new internal repository.

        Args:
            request: The repository creation request payload.
            tenant: Optional tenant subdomain to scope the request.
            user_claim: Optional user identity claims.

        Returns:
            Repository: The created repository instance.

        Raises:
            DMSInvalidArgumentException: If the request payload is invalid.
            DMSPermissionDeniedException: If the access token is invalid or expired.
            DMSRuntimeException: If the server encounters an internal error.
        """
        logger.info("Onboarding repository '%s'", request.to_dict())
        response = self._http.post(
            path=endpoints.REPOSITORIES,
            payload={"repository": request.to_dict()},
            tenant_subdomain=tenant,
            user_claim=user_claim,
        )
        repo = Repository.from_dict(response.json())
        logger.info("Repository onboarded successfully with id '%s'", repo.id)
        return repo

    @record_metrics(Module.DMS, Operation.DMS_GET_ALL_REPOSITORIES)
    def get_all_repositories(
        self,
        tenant: Optional[str] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> list[Repository]:
        """Retrieve all onboarded repositories.

        Args:
            tenant: Optional tenant subdomain.
            user_claim: Optional user identity claims.

        Returns:
            list[Repository]: List of all repositories.

        Raises:
            DMSPermissionDeniedException: If the access token is invalid or expired.
            DMSRuntimeException: If the server encounters an internal error.
        """
        logger.info("Fetching all repositories")
        response = self._http.get(
            path=endpoints.REPOSITORIES,
            tenant_subdomain=tenant,
            user_claim=user_claim,
            headers={"Accept": "application/vnd.sap.sdm.repositories+json;version=3"},
        )
        data = response.json()
        infos = data.get("repoAndConnectionInfos", [])
        repos = [Repository.from_dict(item["repository"]) for item in infos]
        logger.info("Fetched %d repositories", len(repos))
        return repos
    

    @record_metrics(Module.DMS, Operation.DMS_GET_REPOSITORY)
    def get_repository(
        self,
        repo_id: str,
        tenant: Optional[str] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> Repository:
        """Retrieve details of a specific repository.

        Args:
            repo_id: The repository UUID.
            tenant: Optional tenant subdomain.
            user_claim: Optional user identity claims.

        Returns:
            Repository: The repository details.

        Raises:
            DMSObjectNotFoundException: If the repository does not exist.
            DMSPermissionDeniedException: If the access token is invalid or expired.
            DMSRuntimeException: If the server encounters an internal error.
        """
        logger.info("Fetching repository '%s'", repo_id)
        response = self._http.get(
            path=f"{endpoints.REPOSITORIES}/{repo_id}",
            tenant_subdomain=tenant,
            user_claim=user_claim,
        )
        return Repository.from_dict(response.json()["repository"])


    @record_metrics(Module.DMS, Operation.DMS_UPDATE_REPOSITORY)
    def update_repository(
        self,
        repo_id: str,
        request: UpdateRepoRequest,
        tenant: Optional[str] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> Repository:
        """Update metadata parameters of a repository.

        Args:
            repo_id: The repository UUID.
            request: The update request payload.
            tenant: Optional tenant subdomain.
            user_claim: Optional user identity claims.

        Returns:
            Repository: The updated repository.

        Raises:
            DMSObjectNotFoundException: If the repository does not exist.
            DMSInvalidArgumentException: If the request payload is invalid.
            DMSPermissionDeniedException: If the access token is invalid or expired.
            DMSRuntimeException: If the server encounters an internal error.
        """
        if not repo_id or not repo_id.strip():
            raise ValueError("repo_id must not be empty")
        logger.info("Updating repository '%s'", repo_id)
        response = self._http.put(
            path=f"{endpoints.REPOSITORIES}/{repo_id}",
            payload=request.to_dict(),
            tenant_subdomain=tenant,
            user_claim=user_claim,
        )
        repo = Repository.from_dict(response.json())
        logger.info("Repository '%s' updated successfully", repo_id)
        return repo
    

    @record_metrics(Module.DMS, Operation.DMS_DELETE_REPOSITORY)
    def delete_repository(
        self,
        repo_id: str,
        tenant: Optional[str] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> None:
        """Delete a specific repository.

        Args:
            repo_id: The repository UUID.
            tenant: Optional tenant subdomain.
            user_claim: Optional user identity claims.
        
        Raises:
            DMSObjectNotFoundException: If the repository does not exist.
            DMSInvalidArgumentException: If the request payload is invalid.
            DMSPermissionDeniedException: If the access token is invalid or expired.
            DMSRuntimeException: If the server encounters an internal error.
        """
        self._http.delete(
            path=f"{endpoints.REPOSITORIES}/{repo_id}",
            tenant_subdomain=tenant,
            user_claim=user_claim,
        )


    @record_metrics(Module.DMS, Operation.DMS_CREATE_CONFIG)
    def create_config(
        self,
        request: CreateConfigRequest,
        tenant: Optional[str] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> RepositoryConfig:
        """Create a new repository configuration.

        Args:
            request: The config creation request payload.
            tenant: Optional tenant subdomain.
            user_claim: Optional user identity claims.

        Returns:
            RepositoryConfig: The created configuration.

        Raises:
            DMSInvalidArgumentException: If the request payload is invalid.
            DMSPermissionDeniedException: If the access token is invalid or expired.
            DMSRuntimeException: If the server encounters an internal error.
        """
        logger.info("Creating config '%s'", request.config_name)
        response = self._http.post(
            path=endpoints.CONFIGS,
            payload=request.to_dict(),
            tenant_subdomain=tenant,
            user_claim=user_claim,
        )
        config = RepositoryConfig.from_dict(response.json())
        logger.info("Config created successfully with id '%s'", config.id)
        return config


    @record_metrics(Module.DMS, Operation.DMS_GET_CONFIGS)
    def get_configs(
        self,
        tenant: Optional[str] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> list[RepositoryConfig]:
        """Retrieve all repository configurations.

        Args:
            tenant: Optional tenant subdomain.
            user_claim: Optional user identity claims.

        Returns:
            list[RepositoryConfig]: List of all configurations.

        Raises:
            DMSPermissionDeniedException: If the access token is invalid or expired.
            DMSRuntimeException: If the server encounters an internal error.
        """
        logger.info("Fetching all configs")
        response = self._http.get(
            path=endpoints.CONFIGS,
            tenant_subdomain=tenant,
            user_claim=user_claim,
        )
        configs = [RepositoryConfig.from_dict(c) for c in response.json()]
        logger.info("Fetched %d configs", len(configs))
        return configs

    @record_metrics(Module.DMS, Operation.DMS_UPDATE_CONFIG)
    def update_config(
        self,
        config_id: str,
        request: UpdateConfigRequest,
        tenant: Optional[str] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> RepositoryConfig:
        """Update a repository configuration.

        Args:
            config_id: The configuration UUID.
            request: The update request payload.
            tenant: Optional tenant subdomain.
            user_claim: Optional user identity claims.

        Returns:
            RepositoryConfig: The updated configuration.

        Raises:
            DMSPermissionDeniedException: If the access token is invalid or expired.
            DMSRuntimeException: If the server encounters an internal error.
        """
        if not config_id or not config_id.strip():
            raise ValueError("config_id must not be empty")
        logger.info("Updating config '%s'", config_id)
        response = self._http.put(
            path=f"{endpoints.CONFIGS}/{config_id}",
            payload=request.to_dict(),
            tenant_subdomain=tenant,
            user_claim=user_claim,
        )
        config = RepositoryConfig.from_dict(response.json())
        logger.info("Config '%s' updated successfully", config_id)
        return config

    @record_metrics(Module.DMS, Operation.DMS_DELETE_CONFIG)
    def delete_config(
        self,
        config_id: str,
        tenant: Optional[str] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> None:
        """Delete a repository configuration.

        Args:
            config_id: The configuration UUID.
            tenant: Optional tenant subdomain.
            user_claim: Optional user identity claims.

        Raises:
            ValueError: If config_id is empty.
            DMSObjectNotFoundException: If the config does not exist.
            DMSPermissionDeniedException: If the access token is invalid or expired.
            DMSRuntimeException: If the server encounters an internal error.
        """
        if not config_id or not config_id.strip():
            raise ValueError("config_id must not be empty")
        logger.info("Deleting config '%s'", config_id)
        self._http.delete(
            path=f"{endpoints.CONFIGS}/{config_id}",
            tenant_subdomain=tenant,
            user_claim=user_claim,
        )
        logger.info("Config '%s' deleted successfully", config_id)