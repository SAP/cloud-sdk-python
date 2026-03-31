import logging
from typing import BinaryIO, Dict, List, Optional, Union
from requests import Response
from sap_cloud_sdk.dms.model import (
    DMSCredentials,
    InternalRepoRequest,
    Repository,
    UserClaim,
    UpdateRepoRequest,
    CreateConfigRequest,
    RepositoryConfig,
    UpdateConfigRequest,
    Ace,
    Acl,
    ChildrenPage,
    CmisObject,
    Document,
    Folder,
    _prop_val,
)
from sap_cloud_sdk.dms._auth import Auth
from sap_cloud_sdk.dms._http import HttpInvoker
from sap_cloud_sdk.dms import _endpoints as endpoints
from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CMIS property helpers
# ---------------------------------------------------------------------------


def _build_properties(props: Dict[str, str]) -> Dict[str, str]:
    """Encode CMIS properties into indexed form fields.

    ``{"cmis:name": "Doc"} → {"propertyId[0]": "cmis:name", "propertyValue[0]": "Doc"}``
    """
    form: Dict[str, str] = {}
    for idx, (key, val) in enumerate(props.items()):
        form[f"propertyId[{idx}]"] = key
        form[f"propertyValue[{idx}]"] = str(val)
    return form


def _build_aces(aces: List[Ace], prefix: str) -> Dict[str, str]:
    """Encode ACE entries into indexed CMIS form fields.

    *prefix* is ``addACEPrincipal`` or ``removeACEPrincipal``.
    """
    perm_prefix = prefix.replace("Principal", "Permission")
    form: Dict[str, str] = {}
    for i, ace in enumerate(aces):
        form[f"{prefix}[{i}]"] = ace.principal_id
        for j, perm in enumerate(ace.permissions):
            form[f"{perm_prefix}[{i}][{j}]"] = perm
    return form


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
        logger.debug(
            "DMSClient initialized for instance '%s'", credentials.instance_name
        )

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

    # ==================================================================
    # CMIS — helpers
    # ==================================================================

    @staticmethod
    def _browser_url(repository_id: str, path: Optional[str] = None) -> str:
        base = f"/browser/{repository_id}/root"
        if path:
            return f"{base}/{path.lstrip('/')}"
        return base

    # ==================================================================
    # CMIS — folder operations
    # ==================================================================

    @record_metrics(Module.DMS, Operation.DMS_CREATE_FOLDER)
    def create_folder(
        self,
        repository_id: str,
        parent_folder_id: str,
        folder_name: str,
        *,
        description: Optional[str] = None,
        path: Optional[str] = None,
        tenant: Optional[str] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> Folder:
        """Create a new folder.

        Args:
            repository_id: Target repository ID.
            parent_folder_id: CMIS objectId of the parent folder.
            folder_name: Name for the new folder.
            description: Optional folder description.
            path: Optional directory path (appended to /browser/{repo_id}/root/).
            tenant: Optional subscriber subdomain.
            user_claim: Optional user identity claims forwarded to DMS.

        Returns:
            Folder: The created folder.

        Raises:
            DMSInvalidArgumentException: If the request payload is invalid.
            DMSObjectNotFoundException: If the parent folder is not found.
            DMSPermissionDeniedException: If the access token is invalid.
            DMSRuntimeException: If the server encounters an internal error.
        """
        cmis_props: Dict[str, str] = {
            "cmis:name": folder_name,
            "cmis:objectTypeId": "cmis:folder",
        }
        if description is not None:
            cmis_props["cmis:description"] = description

        form_data: Dict[str, str] = {
            "cmisaction": "createFolder",
            "objectId": parent_folder_id,
            "_charset_": "UTF-8",
        }
        form_data.update(_build_properties(cmis_props))

        logger.info("Creating folder '%s' in repo '%s'", folder_name, repository_id)
        response = self._http.post_form(
            self._browser_url(repository_id, path),
            data=form_data,
            tenant_subdomain=tenant,
            user_claim=user_claim,
        )
        return Folder.from_dict(response.json())

    # ==================================================================
    # CMIS — document operations
    # ==================================================================

    @record_metrics(Module.DMS, Operation.DMS_CREATE_DOCUMENT)
    def create_document(
        self,
        repository_id: str,
        parent_folder_id: str,
        document_name: str,
        file: BinaryIO,
        *,
        mime_type: Optional[str] = None,
        description: Optional[str] = None,
        path: Optional[str] = None,
        tenant: Optional[str] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> Document:
        """Create a new document with content.

        Args:
            repository_id: Target repository ID.
            parent_folder_id: Parent folder CMIS objectId.
            document_name: File name for the document.
            file: Readable binary stream with the content.
            mime_type: MIME type (e.g. ``application/pdf``). Defaults to
                ``application/octet-stream`` when not provided.
            description: Optional document description.
            path: Optional directory path.
            tenant: Optional subscriber subdomain.
            user_claim: Optional user identity claims forwarded to DMS.

        Returns:
            Document: The created document.

        Raises:
            DMSInvalidArgumentException: If the request payload is invalid.
            DMSObjectNotFoundException: If the parent folder is not found.
            DMSPermissionDeniedException: If the access token is invalid.
            DMSRuntimeException: If the server encounters an internal error.
        """
        cmis_props: Dict[str, str] = {
            "cmis:name": document_name,
            "cmis:objectTypeId": "cmis:document",
        }
        if description is not None:
            cmis_props["cmis:description"] = description

        form_data: Dict[str, str] = {
            "cmisaction": "createDocument",
            "objectId": parent_folder_id,
            "_charset_": "UTF-8",
        }
        form_data.update(_build_properties(cmis_props))

        logger.info("Creating document '%s' in repo '%s'", document_name, repository_id)
        response = self._http.post_form(
            self._browser_url(repository_id, path),
            data=form_data,
            files={
                "media": (document_name, file, mime_type or "application/octet-stream")
            },
            tenant_subdomain=tenant,
            user_claim=user_claim,
        )
        return Document.from_dict(response.json())

    # ==================================================================
    # CMIS — versioning
    # ==================================================================

    @record_metrics(Module.DMS, Operation.DMS_CHECK_OUT)
    def check_out(
        self,
        repository_id: str,
        document_id: str,
        *,
        tenant: Optional[str] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> Document:
        """Check out a document, creating a Private Working Copy (PWC).

        Args:
            repository_id: Target repository ID.
            document_id: Document to check out.
            tenant: Optional subscriber subdomain.
            user_claim: Optional user identity claims.

        Returns:
            Document: The Private Working Copy.

        Raises:
            DMSObjectNotFoundException: If the document is not found.
            DMSPermissionDeniedException: If the access token is invalid.
            DMSRuntimeException: If the server encounters an internal error.
        """
        form_data: Dict[str, str] = {
            "cmisaction": "checkOut",
            "objectId": document_id,
            "_charset_": "UTF-8",
        }
        logger.info(
            "Checking out document '%s' in repo '%s'", document_id, repository_id
        )
        response = self._http.post_form(
            self._browser_url(repository_id),
            data=form_data,
            tenant_subdomain=tenant,
            user_claim=user_claim,
        )
        return Document.from_dict(response.json())

    @record_metrics(Module.DMS, Operation.DMS_CHECK_IN)
    def check_in(
        self,
        repository_id: str,
        document_id: str,
        *,
        major: bool = True,
        file: Optional[BinaryIO] = None,
        file_name: Optional[str] = None,
        mime_type: Optional[str] = None,
        checkin_comment: Optional[str] = None,
        tenant: Optional[str] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> Document:
        """Check in a Private Working Copy, creating a new version.

        Args:
            repository_id: Target repository ID.
            document_id: PWC object ID.
            major: True for a major version, False for minor.
            file: Optional updated content stream.
            file_name: File name when providing new content.
            mime_type: MIME type when providing new content.
            checkin_comment: Optional version comment.
            tenant: Optional subscriber subdomain.
            user_claim: Optional user identity claims.

        Returns:
            Document: The new document version.

        Raises:
            DMSObjectNotFoundException: If the document is not found.
            DMSPermissionDeniedException: If the access token is invalid.
            DMSRuntimeException: If the server encounters an internal error.
        """
        form_data: Dict[str, str] = {
            "cmisaction": "checkIn",
            "objectId": document_id,
            "major": str(major).lower(),
            "_charset_": "UTF-8",
        }
        if checkin_comment is not None:
            form_data["checkinComment"] = checkin_comment

        files = None
        if file is not None:
            files = {
                "content": (
                    file_name or "content",
                    file,
                    mime_type or "application/octet-stream",
                )
            }

        logger.info(
            "Checking in document '%s' in repo '%s'", document_id, repository_id
        )
        response = self._http.post_form(
            self._browser_url(repository_id),
            data=form_data,
            files=files,
            tenant_subdomain=tenant,
            user_claim=user_claim,
        )
        return Document.from_dict(response.json())

    @record_metrics(Module.DMS, Operation.DMS_CANCEL_CHECK_OUT)
    def cancel_check_out(
        self,
        repository_id: str,
        document_id: str,
        *,
        tenant: Optional[str] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> None:
        """Cancel a check-out and discard the Private Working Copy.

        Args:
            repository_id: Target repository ID.
            document_id: PWC object ID.
            tenant: Optional subscriber subdomain.
            user_claim: Optional user identity claims.

        Raises:
            DMSObjectNotFoundException: If the document is not found.
            DMSPermissionDeniedException: If the access token is invalid.
            DMSRuntimeException: If the server encounters an internal error.
        """
        form_data: Dict[str, str] = {
            "cmisaction": "cancelCheckOut",
            "objectId": document_id,
            "_charset_": "UTF-8",
        }
        logger.info(
            "Cancelling check-out for '%s' in repo '%s'", document_id, repository_id
        )
        self._http.post_form(
            self._browser_url(repository_id),
            data=form_data,
            tenant_subdomain=tenant,
            user_claim=user_claim,
        )

    # ==================================================================
    # CMIS — ACL operations
    # ==================================================================

    @record_metrics(Module.DMS, Operation.DMS_APPLY_ACL)
    def apply_acl(
        self,
        repository_id: str,
        object_id: str,
        *,
        add_aces: Optional[List[Ace]] = None,
        remove_aces: Optional[List[Ace]] = None,
        acl_propagation: str = "propagate",
        tenant: Optional[str] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> Acl:
        """Get, add, or remove access control entries on an object.

        When neither *add_aces* nor *remove_aces* is provided the current
        ACL is fetched (HTTP GET).  Otherwise the CMIS ``applyACL`` action
        is executed (HTTP POST) with the supplied entries.

        Args:
            repository_id: Target repository ID.
            object_id: Document or folder CMIS objectId.
            add_aces: Optional ACE entries to grant.
            remove_aces: Optional ACE entries to revoke.
            acl_propagation: ACL propagation mode — ``"propagate"``,
                ``"objectonly"``, or ``"repositorydetermined"``.
            tenant: Optional subscriber subdomain.
            user_claim: Optional user identity claims forwarded to DMS.

        Returns:
            Acl: The current or updated ACL.

        Raises:
            DMSObjectNotFoundException: If the object is not found.
            DMSPermissionDeniedException: If the access token is invalid.
            DMSRuntimeException: If the server encounters an internal error.
        """
        if not add_aces and not remove_aces:
            # Read-only: fetch current ACL
            logger.info(
                "Fetching ACL for object '%s' in repo '%s'", object_id, repository_id
            )
            response = self._http.get(
                self._browser_url(repository_id),
                params={"objectId": object_id, "cmisselector": "acl"},
                tenant_subdomain=tenant,
                user_claim=user_claim,
            )
            return Acl.from_dict(response.json())

        form_data: Dict[str, str] = {
            "cmisaction": "applyACL",
            "objectId": object_id,
            "ACLPropagation": acl_propagation,
            "_charset_": "UTF-8",
        }
        if add_aces:
            form_data.update(_build_aces(add_aces, prefix="addACEPrincipal"))
        if remove_aces:
            form_data.update(_build_aces(remove_aces, prefix="removeACEPrincipal"))

        logger.info(
            "Applying ACL to object '%s' in repo '%s'", object_id, repository_id
        )
        response = self._http.post_form(
            self._browser_url(repository_id),
            data=form_data,
            tenant_subdomain=tenant,
            user_claim=user_claim,
        )
        return Acl.from_dict(response.json())

    # ==================================================================
    # CMIS — object read operations
    # ==================================================================

    @record_metrics(Module.DMS, Operation.DMS_GET_OBJECT)
    def get_object(
        self,
        repository_id: str,
        object_id: str,
        *,
        filter: Optional[str] = None,
        include_acl: bool = False,
        include_allowable_actions: bool = False,
        succinct: bool = True,
        tenant: Optional[str] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> Union[Folder, Document, CmisObject]:
        """Retrieve a CMIS object by its ID.

        Automatically returns a :class:`Folder` or :class:`Document`
        based on the ``cmis:baseTypeId`` value; falls back to
        :class:`CmisObject` for unknown types.

        Args:
            repository_id: Target repository ID.
            object_id: CMIS objectId to retrieve.
            filter: Comma-separated property list (e.g. ``"*"`` for all).
            include_acl: Include ACL data in the response.
            include_allowable_actions: Include allowable actions.
            succinct: Use succinct property format.
            tenant: Optional subscriber subdomain.
            user_claim: Optional user identity claims.

        Returns:
            Folder, Document, or CmisObject depending on the base type.

        Raises:
            DMSObjectNotFoundException: If the object is not found.
            DMSPermissionDeniedException: If the access token is invalid.
            DMSRuntimeException: If the server encounters an internal error.
        """
        params: Dict[str, str] = {
            "objectId": object_id,
            "cmisselector": "object",
        }
        if filter:
            params["filter"] = filter
        if include_acl:
            params["includeACL"] = "true"
        if include_allowable_actions:
            params["includeAllowableActions"] = "true"
        if succinct:
            params["succinct"] = "true"

        logger.info("Getting object '%s' from repo '%s'", object_id, repository_id)
        response = self._http.get(
            self._browser_url(repository_id),
            params=params,
            tenant_subdomain=tenant,
            user_claim=user_claim,
        )
        data = response.json()
        props = data.get("succinctProperties") or data.get("properties") or {}
        base_type = _prop_val(props, "cmis:baseTypeId") or ""
        if base_type == "cmis:document":
            return Document.from_dict(data)
        if base_type == "cmis:folder":
            return Folder.from_dict(data)
        return CmisObject.from_dict(data)

    @record_metrics(Module.DMS, Operation.DMS_GET_CONTENT)
    def get_content(
        self,
        repository_id: str,
        document_id: str,
        *,
        download: Optional[str] = None,
        stream_id: Optional[str] = None,
        filename: Optional[str] = None,
        tenant: Optional[str] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> Response:
        """Download the content stream of a document.

        Returns the raw :class:`requests.Response` with ``stream=True``
        so the caller can iterate over chunks or read all bytes::

            resp = client.get_content(repo_id, doc_id, download="attachment")
            with open("file.pdf", "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            resp.close()

        Args:
            repository_id: Target repository ID.
            document_id: Document CMIS objectId.
            download: Download disposition — ``"attachment"`` (save-as) or
                ``"inline"`` (display in browser). Omit to let the server
                decide.
            stream_id: Rendition stream identifier (e.g.
                ``"sap:zipRendition"``). When omitted the primary content
                stream is returned.
            filename: Override the file name in the ``Content-Disposition``
                response header.
            tenant: Optional subscriber subdomain.
            user_claim: Optional user identity claims.

        Returns:
            Response: Raw streaming response. Caller must close it.

        Raises:
            DMSObjectNotFoundException: If the document is not found.
            DMSPermissionDeniedException: If the access token is invalid.
            DMSRuntimeException: If the server encounters an internal error.
        """
        params: Dict[str, str] = {
            "objectId": document_id,
            "cmisselector": "content",
        }
        if download:
            params["download"] = download
        if stream_id:
            params["streamId"] = stream_id
        if filename:
            params["filename"] = filename

        logger.info(
            "Getting content for document '%s' from repo '%s'",
            document_id,
            repository_id,
        )
        return self._http.get_stream(
            self._browser_url(repository_id),
            params=params,
            tenant_subdomain=tenant,
            user_claim=user_claim,
        )

    @record_metrics(Module.DMS, Operation.DMS_UPDATE_PROPERTIES)
    def update_properties(
        self,
        repository_id: str,
        object_id: str,
        properties: Dict[str, str],
        *,
        change_token: Optional[str] = None,
        tenant: Optional[str] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> Union[Folder, Document, CmisObject]:
        """Update properties of an existing CMIS object.

        Args:
            repository_id: Target repository ID.
            object_id: CMIS objectId to update.
            properties: Map of property IDs to new values
                (e.g. ``{"cmis:name": "Renamed", "cmis:description": "New desc"}``)
            change_token: Optional concurrency token for optimistic locking.
            tenant: Optional subscriber subdomain.
            user_claim: Optional user identity claims.

        Returns:
            Folder, Document, or CmisObject depending on the base type.

        Raises:
            DMSObjectNotFoundException: If the object is not found.
            DMSPermissionDeniedException: If the access token is invalid.
            DMSRuntimeException: If the server encounters an internal error.
        """
        form_data: Dict[str, str] = {
            "cmisaction": "update",
            "objectId": object_id,
            "_charset_": "UTF-8",
        }
        if change_token is not None:
            form_data["changeToken"] = change_token
        form_data.update(_build_properties(properties))

        logger.info(
            "Updating properties for object '%s' in repo '%s'", object_id, repository_id
        )
        response = self._http.post_form(
            self._browser_url(repository_id),
            data=form_data,
            tenant_subdomain=tenant,
            user_claim=user_claim,
        )
        data = response.json()
        props = data.get("succinctProperties") or data.get("properties") or {}
        base_type = _prop_val(props, "cmis:baseTypeId") or ""
        if base_type == "cmis:document":
            return Document.from_dict(data)
        if base_type == "cmis:folder":
            return Folder.from_dict(data)
        return CmisObject.from_dict(data)

    @record_metrics(Module.DMS, Operation.DMS_GET_CHILDREN)
    def get_children(
        self,
        repository_id: str,
        folder_id: str,
        *,
        max_items: int = 100,
        skip_count: int = 0,
        order_by: Optional[str] = None,
        filter: Optional[str] = None,
        include_allowable_actions: bool = False,
        include_path_segment: bool = False,
        succinct: bool = True,
        tenant: Optional[str] = None,
        user_claim: Optional[UserClaim] = None,
    ) -> ChildrenPage:
        """List children of a folder (one page).

        Use *skip_count* and *max_items* for pagination.  The returned
        :class:`ChildrenPage` has a ``has_more_items`` flag.

        Args:
            repository_id: Target repository ID.
            folder_id: Parent folder CMIS objectId.
            max_items: Maximum number of items to return (default 100).
            skip_count: Number of items to skip (pagination offset).
            order_by: Sort order (e.g. ``"cmis:creationDate ASC"``).
            filter: Comma-separated property list.
            include_allowable_actions: Include allowable actions per child.
            include_path_segment: Include the path segment per child.
            succinct: Use succinct property format.
            tenant: Optional subscriber subdomain.
            user_claim: Optional user identity claims.

        Returns:
            ChildrenPage: A page of child objects.

        Raises:
            DMSObjectNotFoundException: If the folder is not found.
            DMSPermissionDeniedException: If the access token is invalid.
            DMSRuntimeException: If the server encounters an internal error.
        """
        params: Dict[str, str] = {
            "objectId": folder_id,
            "cmisselector": "children",
            "maxItems": str(max_items),
            "skipCount": str(skip_count),
        }
        if order_by:
            params["orderBy"] = order_by
        if filter:
            params["filter"] = filter
        if include_allowable_actions:
            params["includeAllowableActions"] = "true"
        if include_path_segment:
            params["includePathSegment"] = "true"
        if succinct:
            params["succinct"] = "true"

        logger.info(
            "Getting children of folder '%s' in repo '%s'", folder_id, repository_id
        )
        response = self._http.get(
            self._browser_url(repository_id),
            params=params,
            tenant_subdomain=tenant,
            user_claim=user_claim,
        )
        return ChildrenPage.from_dict(response.json())
