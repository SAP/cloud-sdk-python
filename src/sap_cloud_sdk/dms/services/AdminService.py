from typing import Any, Dict, List,Optional

from sap_cloud_sdk.dms.model.dms_credentials import DMSCredentials
from sap_cloud_sdk.dms.model.repository import Repository
from sap_cloud_sdk.dms.services.BaseService import BaseService 
from sap_cloud_sdk.dms.model.repository_request import InternalRepoRequest, ExternalRepoRequest

_V3_ACCEPT = "application/vnd.sap.sdm.repositories+json;version=3"


class AdminService(BaseService):

    def __init__(self, dms_credentials: DMSCredentials,
                 connect_timeout: Optional[int] = None,
                 read_timeout: Optional[int] = None,) -> None:
        super().__init__(dms_credentials, connect_timeout, read_timeout)

    def get_repositories(self) -> List[Repository]:
        """
        Fetch all connected repositories for the current consumer.

        Returns:
            List of Repository objects.

        Raises:
            DmsException: If the request fails.

        Example:
            >>> repos = client.admin.get_repositories()
            >>> for repo in repos:
            ...     print(repo.name, repo.is_encryption_enabled)
        """

        data: Dict[str, Any] = self._get(
            "/rest/v2/repositories",
            headers={"Accept": _V3_ACCEPT},
        )

        raw_list: List[Dict[str, Any]] = data.get("repoAndConnectionInfos") or []

        repos = [
            Repository.from_dict(item.get("repository") or {})
            for item in raw_list
        ]
        return repos
    
    def onboard_repository(self, repo_request: Union[InternalRepoRequest, ExternalRepoRequest]) -> Repository:
        """
        Onboard a new internal repository.

        Args:
            repo_request: InternalRepoRequest or ExternalRepoRequest object containing repository details.

        Returns:
            Repository object representing the newly onboarded repository.

        Raises:
            DmsException: If the request fails.

        Example:
            >>> repo_req = InternalRepoRequest(display_name="My Repo", is_encryption_enabled=True)
            >>> new_repo = client.admin.onboard_repository(repo_req)
            >>> print(new_repo.id, new_repo.name)
        """

        payload = repo_request.to_dict()

        data: Dict[str, Any] = self._post(
            "/rest/v2/repositories",
            json_data={"repository": payload}
        )
        return Repository.from_dict(data)
    
