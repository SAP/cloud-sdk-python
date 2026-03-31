"""Unit tests for DMSClient admin operations (repositories & configs).

Tests mock HttpInvoker to verify:
- Correct endpoint paths
- Correct payload construction
- Correct response parsing into typed models
- Tenant and user_claim forwarding
- Input validation
"""

from unittest.mock import Mock, patch

import pytest

from sap_cloud_sdk.dms.client import DMSClient
from sap_cloud_sdk.dms.model import (
    CreateConfigRequest,
    DMSCredentials,
    InternalRepoRequest,
    Repository,
    RepositoryConfig,
    UpdateConfigRequest,
    UpdateRepoRequest,
    UserClaim,
)


# ---------------------------------------------------------------
# Helper
# ---------------------------------------------------------------

def _mock_response(data, status_code=200):
    resp = Mock()
    resp.json.return_value = data
    resp.status_code = status_code
    return resp


# ---------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------

_REPO_RESPONSE = {
    "cmisRepositoryId": "cmis-repo-1",
    "createdTime": "2025-06-01T10:00:00Z",
    "id": "repo-uuid-1",
    "lastUpdatedTime": "2025-06-01T12:00:00Z",
    "name": "TestRepo",
    "repositoryCategory": "Collaboration",
    "repositoryParams": [
        {"paramName": "isVersionEnabled", "paramValue": "true"},
    ],
    "repositorySubType": "internal",
    "repositoryType": "internal",
}

_CONFIG_RESPONSE = {
    "id": "cfg-uuid-1",
    "configName": "blockedFileExtensions",
    "configValue": "exe,bat",
    "createdTime": "2025-06-01T10:00:00Z",
    "lastUpdatedTime": "2025-06-01T12:00:00Z",
    "serviceInstanceId": "svc-inst-1",
}


@pytest.fixture
def client():
    with patch("sap_cloud_sdk.dms.client.Auth"):
        with patch("sap_cloud_sdk.dms.client.HttpInvoker") as MockHttp:
            mock_http = Mock()
            MockHttp.return_value = mock_http
            creds = DMSCredentials(
                instance_name="test-instance",
                uri="https://api.example.com",
                client_id="test-client",
                client_secret="test-secret",
                token_url="https://auth.example.com/oauth/token",
                identityzone="test-zone",
            )
            c = DMSClient(creds)
            c._mock_http = mock_http
            yield c


# ---------------------------------------------------------------
# onboard_repository
# ---------------------------------------------------------------

class TestOnboardRepository:
    def test_basic(self, client):
        client._mock_http.post.return_value = _mock_response(_REPO_RESPONSE)
        request = InternalRepoRequest(displayName="TestRepo")

        repo = client.onboard_repository(request)

        assert isinstance(repo, Repository)
        assert repo.id == "repo-uuid-1"
        assert repo.name == "TestRepo"

        call_args = client._mock_http.post.call_args
        assert call_args[1]["path"] == "/rest/v2/repositories"
        payload = call_args[1]["payload"]
        assert "repository" in payload
        assert payload["repository"]["displayName"] == "TestRepo"

    def test_with_tenant_and_user_claim(self, client):
        client._mock_http.post.return_value = _mock_response(_REPO_RESPONSE)
        request = InternalRepoRequest(displayName="TestRepo")
        claim = UserClaim(x_ecm_user_enc="alice@sap.com")

        client.onboard_repository(request, tenant="t1", user_claim=claim)

        call_args = client._mock_http.post.call_args
        assert call_args[1]["tenant_subdomain"] == "t1"
        assert call_args[1]["user_claim"] is claim

    def test_with_versioning_enabled(self, client):
        client._mock_http.post.return_value = _mock_response(_REPO_RESPONSE)
        request = InternalRepoRequest(displayName="VersRepo", isVersionEnabled=True)

        repo = client.onboard_repository(request)

        payload = client._mock_http.post.call_args[1]["payload"]
        assert payload["repository"]["isVersionEnabled"] is True


# ---------------------------------------------------------------
# get_all_repositories
# ---------------------------------------------------------------

class TestGetAllRepositories:
    def test_basic(self, client):
        client._mock_http.get.return_value = _mock_response({
            "repoAndConnectionInfos": [
                {"repository": _REPO_RESPONSE},
            ]
        })

        repos = client.get_all_repositories()

        assert len(repos) == 1
        assert isinstance(repos[0], Repository)
        assert repos[0].id == "repo-uuid-1"

        call_args = client._mock_http.get.call_args
        assert call_args[1]["path"] == "/rest/v2/repositories"
        assert call_args[1]["headers"]["Accept"] == "application/vnd.sap.sdm.repositories+json;version=3"

    def test_empty_list(self, client):
        client._mock_http.get.return_value = _mock_response({
            "repoAndConnectionInfos": []
        })

        repos = client.get_all_repositories()

        assert repos == []

    def test_multiple_repos(self, client):
        repo2 = {**_REPO_RESPONSE, "id": "repo-uuid-2", "name": "Repo2"}
        client._mock_http.get.return_value = _mock_response({
            "repoAndConnectionInfos": [
                {"repository": _REPO_RESPONSE},
                {"repository": repo2},
            ]
        })

        repos = client.get_all_repositories()

        assert len(repos) == 2
        assert repos[1].id == "repo-uuid-2"

    def test_with_tenant(self, client):
        client._mock_http.get.return_value = _mock_response({
            "repoAndConnectionInfos": []
        })

        client.get_all_repositories(tenant="sub1")

        assert client._mock_http.get.call_args[1]["tenant_subdomain"] == "sub1"


# ---------------------------------------------------------------
# get_repository
# ---------------------------------------------------------------

class TestGetRepository:
    def test_basic(self, client):
        client._mock_http.get.return_value = _mock_response({
            "repository": _REPO_RESPONSE
        })

        repo = client.get_repository("repo-uuid-1")

        assert isinstance(repo, Repository)
        assert repo.name == "TestRepo"
        assert client._mock_http.get.call_args[1]["path"] == "/rest/v2/repositories/repo-uuid-1"

    def test_with_tenant_and_user_claim(self, client):
        client._mock_http.get.return_value = _mock_response({
            "repository": _REPO_RESPONSE
        })
        claim = UserClaim(x_ecm_user_enc="bob@sap.com")

        client.get_repository("repo-uuid-1", tenant="t1", user_claim=claim)

        call_args = client._mock_http.get.call_args
        assert call_args[1]["tenant_subdomain"] == "t1"
        assert call_args[1]["user_claim"] is claim


# ---------------------------------------------------------------
# update_repository
# ---------------------------------------------------------------

class TestUpdateRepository:
    def test_basic(self, client):
        client._mock_http.put.return_value = _mock_response(_REPO_RESPONSE)
        request = UpdateRepoRequest(description="Updated desc")

        repo = client.update_repository("repo-uuid-1", request)

        assert isinstance(repo, Repository)
        call_args = client._mock_http.put.call_args
        assert call_args[1]["path"] == "/rest/v2/repositories/repo-uuid-1"
        payload = call_args[1]["payload"]
        assert "repository" in payload
        assert payload["repository"]["description"] == "Updated desc"

    def test_empty_repo_id_raises_value_error(self, client):
        request = UpdateRepoRequest(description="x")

        with pytest.raises(ValueError, match="repo_id must not be empty"):
            client.update_repository("", request)

    def test_whitespace_repo_id_raises_value_error(self, client):
        request = UpdateRepoRequest(description="x")

        with pytest.raises(ValueError, match="repo_id must not be empty"):
            client.update_repository("   ", request)

    def test_with_tenant(self, client):
        client._mock_http.put.return_value = _mock_response(_REPO_RESPONSE)
        request = UpdateRepoRequest(description="d")

        client.update_repository("repo-uuid-1", request, tenant="t1")

        assert client._mock_http.put.call_args[1]["tenant_subdomain"] == "t1"


# ---------------------------------------------------------------
# delete_repository
# ---------------------------------------------------------------

class TestDeleteRepository:
    def test_basic(self, client):
        client._mock_http.delete.return_value = _mock_response(None, status_code=204)

        client.delete_repository("repo-uuid-1")

        call_args = client._mock_http.delete.call_args
        assert call_args[1]["path"] == "/rest/v2/repositories/repo-uuid-1"

    def test_with_tenant_and_user_claim(self, client):
        client._mock_http.delete.return_value = _mock_response(None, status_code=204)
        claim = UserClaim(x_ecm_user_enc="admin@sap.com")

        client.delete_repository("repo-uuid-1", tenant="t1", user_claim=claim)

        call_args = client._mock_http.delete.call_args
        assert call_args[1]["tenant_subdomain"] == "t1"
        assert call_args[1]["user_claim"] is claim


# ---------------------------------------------------------------
# create_config
# ---------------------------------------------------------------

class TestCreateConfig:
    def test_basic(self, client):
        client._mock_http.post.return_value = _mock_response(_CONFIG_RESPONSE)
        request = CreateConfigRequest(
            config_name="blockedFileExtensions",
            config_value="exe,bat",
        )

        config = client.create_config(request)

        assert isinstance(config, RepositoryConfig)
        assert config.id == "cfg-uuid-1"
        assert config.config_name == "blockedFileExtensions"
        assert config.config_value == "exe,bat"

        call_args = client._mock_http.post.call_args
        assert call_args[1]["path"] == "/rest/v2/configs"
        payload = call_args[1]["payload"]
        assert payload["configName"] == "blockedFileExtensions"
        assert payload["configValue"] == "exe,bat"

    def test_with_tenant(self, client):
        client._mock_http.post.return_value = _mock_response(_CONFIG_RESPONSE)
        request = CreateConfigRequest(
            config_name="blockedFileExtensions", config_value="exe",
        )

        client.create_config(request, tenant="sub1")

        assert client._mock_http.post.call_args[1]["tenant_subdomain"] == "sub1"


# ---------------------------------------------------------------
# get_configs
# ---------------------------------------------------------------

class TestGetConfigs:
    def test_basic(self, client):
        client._mock_http.get.return_value = _mock_response([_CONFIG_RESPONSE])

        configs = client.get_configs()

        assert len(configs) == 1
        assert isinstance(configs[0], RepositoryConfig)
        assert configs[0].config_name == "blockedFileExtensions"
        assert client._mock_http.get.call_args[1]["path"] == "/rest/v2/configs"

    def test_empty_list(self, client):
        client._mock_http.get.return_value = _mock_response([])

        configs = client.get_configs()

        assert configs == []

    def test_multiple_configs(self, client):
        cfg2 = {**_CONFIG_RESPONSE, "id": "cfg-uuid-2", "configName": "tempspaceMaxContentSize"}
        client._mock_http.get.return_value = _mock_response([_CONFIG_RESPONSE, cfg2])

        configs = client.get_configs()

        assert len(configs) == 2
        assert configs[1].config_name == "tempspaceMaxContentSize"

    def test_with_user_claim(self, client):
        client._mock_http.get.return_value = _mock_response([])
        claim = UserClaim(x_ecm_user_enc="admin@sap.com")

        client.get_configs(user_claim=claim)

        assert client._mock_http.get.call_args[1]["user_claim"] is claim


# ---------------------------------------------------------------
# update_config
# ---------------------------------------------------------------

class TestUpdateConfig:
    def test_basic(self, client):
        updated = {**_CONFIG_RESPONSE, "configValue": "exe,bat,sh"}
        client._mock_http.put.return_value = _mock_response(updated)
        request = UpdateConfigRequest(
            id="cfg-uuid-1",
            config_name="blockedFileExtensions",
            config_value="exe,bat,sh",
        )

        config = client.update_config("cfg-uuid-1", request)

        assert isinstance(config, RepositoryConfig)
        assert config.config_value == "exe,bat,sh"

        call_args = client._mock_http.put.call_args
        assert call_args[1]["path"] == "/rest/v2/configs/cfg-uuid-1"

    def test_empty_config_id_raises_value_error(self, client):
        request = UpdateConfigRequest(
            id="x", config_name="n", config_value="v",
        )

        with pytest.raises(ValueError, match="config_id must not be empty"):
            client.update_config("", request)

    def test_with_tenant(self, client):
        client._mock_http.put.return_value = _mock_response(_CONFIG_RESPONSE)
        request = UpdateConfigRequest(
            id="cfg-uuid-1", config_name="n", config_value="v",
        )

        client.update_config("cfg-uuid-1", request, tenant="t1")

        assert client._mock_http.put.call_args[1]["tenant_subdomain"] == "t1"


# ---------------------------------------------------------------
# delete_config
# ---------------------------------------------------------------

class TestDeleteConfig:
    def test_basic(self, client):
        client._mock_http.delete.return_value = _mock_response(None, status_code=204)

        client.delete_config("cfg-uuid-1")

        call_args = client._mock_http.delete.call_args
        assert call_args[1]["path"] == "/rest/v2/configs/cfg-uuid-1"

    def test_empty_config_id_raises_value_error(self, client):
        with pytest.raises(ValueError, match="config_id must not be empty"):
            client.delete_config("")

    def test_with_tenant_and_user_claim(self, client):
        client._mock_http.delete.return_value = _mock_response(None, status_code=204)
        claim = UserClaim(x_ecm_user_enc="admin@sap.com")

        client.delete_config("cfg-uuid-1", tenant="t1", user_claim=claim)

        call_args = client._mock_http.delete.call_args
        assert call_args[1]["tenant_subdomain"] == "t1"
        assert call_args[1]["user_claim"] is claim
