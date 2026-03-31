"""Unit tests for DMSClient CMIS operations.

Tests mock HttpInvoker to verify:
- Correct URL construction
- Correct form-data encoding (cmisaction, objectId, indexed properties)
- Correct file tuple for upload methods
- Response parsing into typed models
"""

from io import BytesIO
from unittest.mock import Mock, patch

import pytest

from sap_cloud_sdk.dms.client import DMSClient, _build_properties, _build_aces
from sap_cloud_sdk.dms.model import (
    Ace, Acl, ChildrenPage, CmisObject, DMSCredentials, Document, Folder, UserClaim,
)


# ---------------------------------------------------------------
# Helper to wrap a dict in a mock Response with .json()
# ---------------------------------------------------------------

def _mock_response(data):
    """Create a Mock that behaves like requests.Response with .json() returning *data*."""
    resp = Mock()
    resp.json.return_value = data
    resp.status_code = 200
    return resp


# ---------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------

_FOLDER_RESPONSE = {
    "succinctProperties": {
        "cmis:objectId": "folder-abc",
        "cmis:name": "NewFolder",
        "cmis:baseTypeId": "cmis:folder",
        "cmis:objectTypeId": "cmis:folder",
        "cmis:createdBy": "admin",
        "cmis:creationDate": 1705320000000,
    }
}

_DOCUMENT_RESPONSE = {
    "succinctProperties": {
        "cmis:objectId": "doc-xyz",
        "cmis:name": "report.pdf",
        "cmis:baseTypeId": "cmis:document",
        "cmis:objectTypeId": "cmis:document",
        "cmis:contentStreamLength": 2048,
        "cmis:contentStreamMimeType": "application/pdf",
        "cmis:contentStreamFileName": "report.pdf",
        "cmis:versionSeriesId": "vs-1",
        "cmis:versionLabel": "1.0",
        "cmis:isLatestVersion": True,
        "cmis:isMajorVersion": True,
        "cmis:isPrivateWorkingCopy": False,
    }
}

_PWC_RESPONSE = {
    "succinctProperties": {
        "cmis:objectId": "pwc-001",
        "cmis:name": "report.pdf",
        "cmis:baseTypeId": "cmis:document",
        "cmis:objectTypeId": "cmis:document",
        "cmis:isPrivateWorkingCopy": True,
        "cmis:isVersionSeriesCheckedOut": True,
    }
}

_ACL_RESPONSE = {
    "aces": [
        {
            "principal": {"principalId": "user1"},
            "permissions": ["cmis:read"],
            "isDirect": True,
        }
    ],
    "isExact": True,
}


@pytest.fixture
def client():
    """Create a DMSClient with a mocked HttpInvoker."""
    creds = DMSCredentials(
        instance_name="test-instance",
        uri="https://api.example.com",
        client_id="test-client",
        client_secret="test-secret",
        token_url="https://auth.example.com/oauth/token",
        identityzone="test-zone",
    )
    with patch("sap_cloud_sdk.dms.client.Auth"), \
         patch("sap_cloud_sdk.dms.client.HttpInvoker") as mock_http_cls:
        mock_http = Mock()
        mock_http_cls.return_value = mock_http
        c = DMSClient(creds)
        # Expose the mock for assertions
        c._mock_http = mock_http
        yield c


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

class TestBuildProperties:
    def test_single_property(self):
        result = _build_properties({"cmis:name": "Doc"})
        assert result == {
            "propertyId[0]": "cmis:name",
            "propertyValue[0]": "Doc",
        }

    def test_multiple_properties(self):
        result = _build_properties({
            "cmis:name": "Doc",
            "cmis:objectTypeId": "cmis:document",
            "cmis:description": "A doc",
        })
        assert result["propertyId[0]"] == "cmis:name"
        assert result["propertyValue[0]"] == "Doc"
        assert result["propertyId[1]"] == "cmis:objectTypeId"
        assert result["propertyValue[1]"] == "cmis:document"
        assert result["propertyId[2]"] == "cmis:description"
        assert result["propertyValue[2]"] == "A doc"

    def test_empty_properties(self):
        assert _build_properties({}) == {}

    def test_integer_value_coerced_to_string(self):
        result = _build_properties({"cmis:contentStreamLength": "1024"})
        assert result["propertyValue[0]"] == "1024"


class TestBuildAces:
    def test_single_ace_single_permission(self):
        ace = Ace(principal_id="user1", permissions=["cmis:read"])
        result = _build_aces([ace], prefix="addACEPrincipal")
        assert result == {
            "addACEPrincipal[0]": "user1",
            "addACEPermission[0][0]": "cmis:read",
        }

    def test_single_ace_multiple_permissions(self):
        ace = Ace(principal_id="user1", permissions=["cmis:read", "cmis:write"])
        result = _build_aces([ace], prefix="addACEPrincipal")
        assert result == {
            "addACEPrincipal[0]": "user1",
            "addACEPermission[0][0]": "cmis:read",
            "addACEPermission[0][1]": "cmis:write",
        }

    def test_multiple_aces(self):
        aces = [
            Ace(principal_id="user1", permissions=["cmis:read"]),
            Ace(principal_id="user2", permissions=["cmis:all"]),
        ]
        result = _build_aces(aces, prefix="removeACEPrincipal")
        assert result["removeACEPrincipal[0]"] == "user1"
        assert result["removeACEPermission[0][0]"] == "cmis:read"
        assert result["removeACEPrincipal[1]"] == "user2"
        assert result["removeACEPermission[1][0]"] == "cmis:all"

    def test_empty_aces(self):
        assert _build_aces([], prefix="addACEPrincipal") == {}


class TestBrowserUrl:
    def test_no_path(self):
        assert DMSClient._browser_url("repo1") == "/browser/repo1/root"

    def test_with_path(self):
        assert DMSClient._browser_url("repo1", "sub/folder") == "/browser/repo1/root/sub/folder"

    def test_strips_leading_slash(self):
        assert DMSClient._browser_url("repo1", "/sub") == "/browser/repo1/root/sub"

    def test_none_path_same_as_no_path(self):
        assert DMSClient._browser_url("repo1", None) == "/browser/repo1/root"


# ---------------------------------------------------------------
# create_folder
# ---------------------------------------------------------------

class TestCreateFolder:
    def test_basic(self, client):
        client._mock_http.post_form.return_value = _mock_response(_FOLDER_RESPONSE)

        folder = client.create_folder("repo1", "parent-id", "NewFolder")

        assert isinstance(folder, Folder)
        assert folder.object_id == "folder-abc"
        assert folder.name == "NewFolder"

        call_args = client._mock_http.post_form.call_args
        assert call_args[0][0] == "/browser/repo1/root"
        data = call_args[1]["data"]
        assert data["cmisaction"] == "createFolder"
        assert data["objectId"] == "parent-id"
        assert data["propertyId[0]"] == "cmis:name"
        assert data["propertyValue[0]"] == "NewFolder"
        assert data["propertyId[1]"] == "cmis:objectTypeId"
        assert data["propertyValue[1]"] == "cmis:folder"
        assert data["_charset_"] == "UTF-8"
        assert call_args[1]["tenant_subdomain"] is None

    def test_with_description(self, client):
        client._mock_http.post_form.return_value = _mock_response(_FOLDER_RESPONSE)

        client.create_folder("repo1", "parent-id", "NewFolder", description="Desc")

        data = client._mock_http.post_form.call_args[1]["data"]
        assert data["propertyId[2]"] == "cmis:description"
        assert data["propertyValue[2]"] == "Desc"

    def test_with_path_and_tenant(self, client):
        client._mock_http.post_form.return_value = _mock_response(_FOLDER_RESPONSE)

        client.create_folder("repo1", "parent-id", "F", path="sub/dir", tenant="t1")

        call_args = client._mock_http.post_form.call_args
        assert call_args[0][0] == "/browser/repo1/root/sub/dir"
        assert call_args[1]["tenant_subdomain"] == "t1"

    def test_with_user_claim(self, client):
        client._mock_http.post_form.return_value = _mock_response(_FOLDER_RESPONSE)
        claim = UserClaim(x_ecm_user_enc="alice@sap.com", x_ecm_add_principals=["~editors"])

        client.create_folder("repo1", "parent-id", "F", user_claim=claim)

        assert client._mock_http.post_form.call_args[1]["user_claim"] is claim



# ---------------------------------------------------------------
# create_document
# ---------------------------------------------------------------

class TestCreateDocument:
    def test_basic(self, client):
        client._mock_http.post_form.return_value = _mock_response(_DOCUMENT_RESPONSE)
        stream = BytesIO(b"hello world")

        doc = client.create_document("repo1", "folder-id", "report.pdf", stream, mime_type="application/pdf")

        assert isinstance(doc, Document)
        assert doc.object_id == "doc-xyz"
        assert doc.content_stream_mime_type == "application/pdf"

        call_args = client._mock_http.post_form.call_args
        assert call_args[0][0] == "/browser/repo1/root"
        data = call_args[1]["data"]
        assert data["cmisaction"] == "createDocument"
        assert data["objectId"] == "folder-id"
        assert data["propertyId[0]"] == "cmis:name"
        assert data["propertyValue[0]"] == "report.pdf"
        assert data["propertyId[1]"] == "cmis:objectTypeId"
        assert data["propertyValue[1]"] == "cmis:document"

        files_arg = call_args[1]["files"]
        assert "media" in files_arg
        assert files_arg["media"][0] == "report.pdf"
        assert files_arg["media"][2] == "application/pdf"

    def test_with_description(self, client):
        client._mock_http.post_form.return_value = _mock_response(_DOCUMENT_RESPONSE)

        client.create_document("repo1", "folder-id", "f.txt", BytesIO(b""), mime_type="text/plain", description="D")

        data = client._mock_http.post_form.call_args[1]["data"]
        assert data["propertyId[2]"] == "cmis:description"
        assert data["propertyValue[2]"] == "D"

    def test_with_tenant(self, client):
        client._mock_http.post_form.return_value = _mock_response(_DOCUMENT_RESPONSE)

        client.create_document("repo1", "fid", "f.txt", BytesIO(b""), mime_type="text/plain", tenant="sub1")

        assert client._mock_http.post_form.call_args[1]["tenant_subdomain"] == "sub1"

    def test_with_user_claim(self, client):
        client._mock_http.post_form.return_value = _mock_response(_DOCUMENT_RESPONSE)
        claim = UserClaim(x_ecm_user_enc="bob@sap.com")

        client.create_document("repo1", "fid", "f.txt", BytesIO(b""), mime_type="text/plain", user_claim=claim)

        assert client._mock_http.post_form.call_args[1]["user_claim"] is claim

    def test_without_mime_type_uses_default(self, client):
        client._mock_http.post_form.return_value = _mock_response(_DOCUMENT_RESPONSE)
        stream = BytesIO(b"binary data")

        client.create_document("repo1", "fid", "data.bin", stream)

        files_arg = client._mock_http.post_form.call_args[1]["files"]
        assert files_arg["media"][2] == "application/octet-stream"


# ---------------------------------------------------------------
# check_out
# ---------------------------------------------------------------

class TestCheckOut:
    def test_basic(self, client):
        client._mock_http.post_form.return_value = _mock_response(_PWC_RESPONSE)

        doc = client.check_out("repo1", "doc-xyz")

        assert isinstance(doc, Document)
        assert doc.object_id == "pwc-001"
        assert doc.is_private_working_copy is True

        data = client._mock_http.post_form.call_args[1]["data"]
        assert data["cmisaction"] == "checkOut"
        assert data["objectId"] == "doc-xyz"

    def test_with_tenant(self, client):
        client._mock_http.post_form.return_value = _mock_response(_PWC_RESPONSE)

        client.check_out("repo1", "doc-xyz", tenant="t1")

        assert client._mock_http.post_form.call_args[1]["tenant_subdomain"] == "t1"

    def test_with_user_claim(self, client):
        client._mock_http.post_form.return_value = _mock_response(_PWC_RESPONSE)
        claim = UserClaim(x_ecm_user_enc="dave@sap.com")

        client.check_out("repo1", "doc-xyz", user_claim=claim)

        assert client._mock_http.post_form.call_args[1]["user_claim"] is claim


# ---------------------------------------------------------------
# check_in
# ---------------------------------------------------------------

class TestCheckIn:
    def test_major_version_no_file(self, client):
        client._mock_http.post_form.return_value = _mock_response(_DOCUMENT_RESPONSE)

        doc = client.check_in("repo1", "pwc-001")

        assert isinstance(doc, Document)
        data = client._mock_http.post_form.call_args[1]["data"]
        assert data["cmisaction"] == "checkIn"
        assert data["objectId"] == "pwc-001"
        assert data["major"] == "true"
        assert client._mock_http.post_form.call_args[1]["files"] is None

    def test_minor_version(self, client):
        client._mock_http.post_form.return_value = _mock_response(_DOCUMENT_RESPONSE)

        client.check_in("repo1", "pwc-001", major=False)

        data = client._mock_http.post_form.call_args[1]["data"]
        assert data["major"] == "false"

    def test_with_file_and_comment(self, client):
        client._mock_http.post_form.return_value = _mock_response(_DOCUMENT_RESPONSE)
        stream = BytesIO(b"updated content")

        client.check_in(
            "repo1", "pwc-001",
            file=stream,
            file_name="report_v2.pdf",
            mime_type="application/pdf",
            checkin_comment="Version 2",
        )

        call_args = client._mock_http.post_form.call_args
        data = call_args[1]["data"]
        assert data["checkinComment"] == "Version 2"

        files_arg = call_args[1]["files"]
        assert "content" in files_arg
        assert files_arg["content"][0] == "report_v2.pdf"
        assert files_arg["content"][2] == "application/pdf"

    def test_file_without_name_uses_default(self, client):
        client._mock_http.post_form.return_value = _mock_response(_DOCUMENT_RESPONSE)

        client.check_in("repo1", "pwc-001", file=BytesIO(b"data"))

        files_arg = client._mock_http.post_form.call_args[1]["files"]
        assert files_arg["content"][0] == "content"
        assert files_arg["content"][2] == "application/octet-stream"

    def test_with_user_claim(self, client):
        client._mock_http.post_form.return_value = _mock_response(_DOCUMENT_RESPONSE)
        claim = UserClaim(x_ecm_user_enc="eve@sap.com", x_ecm_add_principals=["~reviewers"])

        client.check_in("repo1", "pwc-001", user_claim=claim)

        assert client._mock_http.post_form.call_args[1]["user_claim"] is claim


# ---------------------------------------------------------------
# cancel_check_out
# ---------------------------------------------------------------

class TestCancelCheckOut:
    def test_basic(self, client):
        client._mock_http.post_form.return_value = _mock_response({})

        result = client.cancel_check_out("repo1", "pwc-001")

        assert result is None
        data = client._mock_http.post_form.call_args[1]["data"]
        assert data["cmisaction"] == "cancelCheckOut"
        assert data["objectId"] == "pwc-001"

    def test_with_tenant(self, client):
        client._mock_http.post_form.return_value = _mock_response({})

        client.cancel_check_out("repo1", "pwc-001", tenant="sub2")

        assert client._mock_http.post_form.call_args[1]["tenant_subdomain"] == "sub2"

    def test_with_user_claim(self, client):
        client._mock_http.post_form.return_value = _mock_response({})
        claim = UserClaim(x_ecm_user_enc="frank@sap.com")

        client.cancel_check_out("repo1", "pwc-001", user_claim=claim)

        assert client._mock_http.post_form.call_args[1]["user_claim"] is claim


# ---------------------------------------------------------------
# apply_acl
# ---------------------------------------------------------------

class TestApplyAcl:
    def test_get_acl_when_no_aces(self, client):
        """No add/remove => GET current ACL."""
        client._mock_http.get.return_value = _mock_response(_ACL_RESPONSE)

        acl = client.apply_acl("repo1", "obj-99")

        assert isinstance(acl, Acl)
        assert len(acl.aces) == 1
        assert acl.aces[0].principal_id == "user1"

        call_args = client._mock_http.get.call_args
        assert call_args[0][0] == "/browser/repo1/root"
        assert call_args[1]["params"] == {"objectId": "obj-99", "cmisselector": "acl"}

    def test_get_acl_with_tenant(self, client):
        client._mock_http.get.return_value = _mock_response(_ACL_RESPONSE)

        client.apply_acl("repo1", "obj-99", tenant="t1")

        assert client._mock_http.get.call_args[1]["tenant_subdomain"] == "t1"

    def test_get_acl_with_user_claim(self, client):
        client._mock_http.get.return_value = _mock_response(_ACL_RESPONSE)
        claim = UserClaim(x_ecm_user_enc="grace@sap.com")

        client.apply_acl("repo1", "obj-99", user_claim=claim)

        assert client._mock_http.get.call_args[1]["user_claim"] is claim

    def test_add_aces_only(self, client):
        client._mock_http.post_form.return_value = _mock_response(_ACL_RESPONSE)
        aces = [Ace(principal_id="user1", permissions=["cmis:read", "cmis:write"])]

        acl = client.apply_acl("repo1", "obj-99", add_aces=aces)

        assert isinstance(acl, Acl)
        data = client._mock_http.post_form.call_args[1]["data"]
        assert data["cmisaction"] == "applyACL"
        assert data["objectId"] == "obj-99"
        assert data["ACLPropagation"] == "propagate"
        assert data["addACEPrincipal[0]"] == "user1"
        assert data["addACEPermission[0][0]"] == "cmis:read"
        assert data["addACEPermission[0][1]"] == "cmis:write"
        assert not any(k.startswith("removeACE") for k in data)

    def test_remove_aces_only(self, client):
        client._mock_http.post_form.return_value = _mock_response(_ACL_RESPONSE)
        aces = [Ace(principal_id="user1", permissions=["cmis:write"])]

        acl = client.apply_acl("repo1", "obj-99", remove_aces=aces)

        assert isinstance(acl, Acl)
        data = client._mock_http.post_form.call_args[1]["data"]
        assert data["cmisaction"] == "applyACL"
        assert data["removeACEPrincipal[0]"] == "user1"
        assert data["removeACEPermission[0][0]"] == "cmis:write"
        assert not any(k.startswith("addACE") for k in data)

    def test_add_and_remove_together(self, client):
        client._mock_http.post_form.return_value = _mock_response(_ACL_RESPONSE)
        add = [Ace(principal_id="u1", permissions=["cmis:read"])]
        remove = [Ace(principal_id="u2", permissions=["cmis:all"])]

        acl = client.apply_acl("repo1", "obj-99", add_aces=add, remove_aces=remove)

        assert isinstance(acl, Acl)
        data = client._mock_http.post_form.call_args[1]["data"]
        assert data["addACEPrincipal[0]"] == "u1"
        assert data["addACEPermission[0][0]"] == "cmis:read"
        assert data["removeACEPrincipal[0]"] == "u2"
        assert data["removeACEPermission[0][0]"] == "cmis:all"

    def test_multiple_add_aces(self, client):
        client._mock_http.post_form.return_value = _mock_response(_ACL_RESPONSE)
        aces = [
            Ace(principal_id="u1", permissions=["cmis:read"]),
            Ace(principal_id="u2", permissions=["cmis:all"]),
        ]

        client.apply_acl("repo1", "obj-99", add_aces=aces)

        data = client._mock_http.post_form.call_args[1]["data"]
        assert data["addACEPrincipal[0]"] == "u1"
        assert data["addACEPrincipal[1]"] == "u2"

    def test_with_tenant_on_modify(self, client):
        client._mock_http.post_form.return_value = _mock_response(_ACL_RESPONSE)
        aces = [Ace(principal_id="u1", permissions=["cmis:read"])]

        client.apply_acl("repo1", "obj-99", remove_aces=aces, tenant="t1")

        assert client._mock_http.post_form.call_args[1]["tenant_subdomain"] == "t1"

    def test_with_user_claim_on_modify(self, client):
        client._mock_http.post_form.return_value = _mock_response(_ACL_RESPONSE)
        aces = [Ace(principal_id="u1", permissions=["cmis:read"])]
        claim = UserClaim(x_ecm_user_enc="heidi@sap.com")

        client.apply_acl("repo1", "obj-99", add_aces=aces, user_claim=claim)

        assert client._mock_http.post_form.call_args[1]["user_claim"] is claim

    def test_custom_acl_propagation(self, client):
        client._mock_http.post_form.return_value = _mock_response(_ACL_RESPONSE)
        aces = [Ace(principal_id="u1", permissions=["cmis:read"])]

        client.apply_acl("repo1", "obj-99", add_aces=aces, acl_propagation="objectonly")

        data = client._mock_http.post_form.call_args[1]["data"]
        assert data["ACLPropagation"] == "objectonly"


# ---------------------------------------------------------------
# get_object
# ---------------------------------------------------------------

class TestGetObject:
    def test_returns_folder_for_folder_type(self, client):
        client._mock_http.get.return_value = _mock_response(_FOLDER_RESPONSE)

        obj = client.get_object("repo1", "folder-abc")

        assert isinstance(obj, Folder)
        assert obj.object_id == "folder-abc"
        assert obj.name == "NewFolder"

        call_args = client._mock_http.get.call_args
        assert call_args[0][0] == "/browser/repo1/root"
        params = call_args[1]["params"]
        assert params["objectId"] == "folder-abc"
        assert params["cmisselector"] == "object"
        assert params["succinct"] == "true"

    def test_returns_document_for_document_type(self, client):
        client._mock_http.get.return_value = _mock_response(_DOCUMENT_RESPONSE)

        obj = client.get_object("repo1", "doc-xyz")

        assert isinstance(obj, Document)
        assert obj.object_id == "doc-xyz"
        assert obj.content_stream_mime_type == "application/pdf"

    def test_returns_cmis_object_for_unknown_type(self, client):
        client._mock_http.get.return_value = _mock_response({
            "succinctProperties": {
                "cmis:objectId": "item-1",
                "cmis:name": "Item",
                "cmis:baseTypeId": "cmis:item",
                "cmis:objectTypeId": "cmis:item",
            }
        })

        obj = client.get_object("repo1", "item-1")

        assert isinstance(obj, CmisObject)
        assert not isinstance(obj, (Folder, Document))
        assert obj.object_id == "item-1"

    def test_with_filter_and_include_acl(self, client):
        client._mock_http.get.return_value = _mock_response(_FOLDER_RESPONSE)

        client.get_object("repo1", "folder-abc", filter="*", include_acl=True)

        params = client._mock_http.get.call_args[1]["params"]
        assert params["filter"] == "*"
        assert params["includeACL"] == "true"

    def test_with_include_allowable_actions(self, client):
        client._mock_http.get.return_value = _mock_response(_FOLDER_RESPONSE)

        client.get_object("repo1", "folder-abc", include_allowable_actions=True)

        params = client._mock_http.get.call_args[1]["params"]
        assert params["includeAllowableActions"] == "true"

    def test_without_succinct(self, client):
        resp = {
            "properties": {
                "cmis:objectId": {"value": "f1"},
                "cmis:name": {"value": "F"},
                "cmis:baseTypeId": {"value": "cmis:folder"},
                "cmis:objectTypeId": {"value": "cmis:folder"},
            }
        }
        client._mock_http.get.return_value = _mock_response(resp)

        obj = client.get_object("repo1", "f1", succinct=False)

        params = client._mock_http.get.call_args[1]["params"]
        assert "succinct" not in params
        assert isinstance(obj, Folder)

    def test_with_tenant_and_user_claim(self, client):
        client._mock_http.get.return_value = _mock_response(_FOLDER_RESPONSE)
        claim = UserClaim(x_ecm_user_enc="alice@sap.com")

        client.get_object("repo1", "folder-abc", tenant="t1", user_claim=claim)

        call_args = client._mock_http.get.call_args
        assert call_args[1]["tenant_subdomain"] == "t1"
        assert call_args[1]["user_claim"] is claim


# ---------------------------------------------------------------
# get_content
# ---------------------------------------------------------------

class TestGetContent:
    def test_basic(self, client):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.content = b"PDF binary data"
        client._mock_http.get_stream.return_value = mock_resp

        resp = client.get_content("repo1", "doc-xyz")

        assert resp is mock_resp
        call_args = client._mock_http.get_stream.call_args
        assert call_args[0][0] == "/browser/repo1/root"
        params = call_args[1]["params"]
        assert params["objectId"] == "doc-xyz"
        assert params["cmisselector"] == "content"

    def test_with_tenant(self, client):
        mock_resp = Mock()
        client._mock_http.get_stream.return_value = mock_resp

        client.get_content("repo1", "doc-xyz", tenant="sub1")

        assert client._mock_http.get_stream.call_args[1]["tenant_subdomain"] == "sub1"

    def test_with_user_claim(self, client):
        mock_resp = Mock()
        client._mock_http.get_stream.return_value = mock_resp
        claim = UserClaim(x_ecm_user_enc="bob@sap.com")

        client.get_content("repo1", "doc-xyz", user_claim=claim)

        assert client._mock_http.get_stream.call_args[1]["user_claim"] is claim

    def test_with_download_attachment(self, client):
        mock_resp = Mock()
        client._mock_http.get_stream.return_value = mock_resp

        client.get_content("repo1", "doc-xyz", download="attachment")

        params = client._mock_http.get_stream.call_args[1]["params"]
        assert params["download"] == "attachment"

    def test_no_download_by_default(self, client):
        mock_resp = Mock()
        client._mock_http.get_stream.return_value = mock_resp

        client.get_content("repo1", "doc-xyz")

        params = client._mock_http.get_stream.call_args[1]["params"]
        assert "download" not in params

    def test_with_stream_id(self, client):
        mock_resp = Mock()
        client._mock_http.get_stream.return_value = mock_resp

        client.get_content("repo1", "doc-xyz", stream_id="sap:zipRendition")

        params = client._mock_http.get_stream.call_args[1]["params"]
        assert params["streamId"] == "sap:zipRendition"

    def test_with_filename(self, client):
        mock_resp = Mock()
        client._mock_http.get_stream.return_value = mock_resp

        client.get_content("repo1", "doc-xyz", filename="report.pdf")

        params = client._mock_http.get_stream.call_args[1]["params"]
        assert params["filename"] == "report.pdf"

    def test_no_stream_id_or_filename_by_default(self, client):
        mock_resp = Mock()
        client._mock_http.get_stream.return_value = mock_resp

        client.get_content("repo1", "doc-xyz")

        params = client._mock_http.get_stream.call_args[1]["params"]
        assert "streamId" not in params
        assert "filename" not in params


# ---------------------------------------------------------------
# update_properties
# ---------------------------------------------------------------

class TestUpdateProperties:
    def test_basic_rename(self, client):
        resp = {
            "succinctProperties": {
                "cmis:objectId": "doc-xyz",
                "cmis:name": "Renamed.pdf",
                "cmis:baseTypeId": "cmis:document",
                "cmis:objectTypeId": "cmis:document",
                "cmis:contentStreamLength": 2048,
                "cmis:contentStreamMimeType": "application/pdf",
            }
        }
        client._mock_http.post_form.return_value = _mock_response(resp)

        obj = client.update_properties("repo1", "doc-xyz", {"cmis:name": "Renamed.pdf"})

        assert isinstance(obj, Document)
        assert obj.name == "Renamed.pdf"

        call_args = client._mock_http.post_form.call_args
        assert call_args[0][0] == "/browser/repo1/root"
        data = call_args[1]["data"]
        assert data["cmisaction"] == "update"
        assert data["objectId"] == "doc-xyz"
        assert data["_charset_"] == "UTF-8"
        assert data["propertyId[0]"] == "cmis:name"
        assert data["propertyValue[0]"] == "Renamed.pdf"

    def test_returns_folder_for_folder_type(self, client):
        client._mock_http.post_form.return_value = _mock_response(_FOLDER_RESPONSE)

        obj = client.update_properties("repo1", "folder-abc", {"cmis:description": "Updated"})

        assert isinstance(obj, Folder)

    def test_with_change_token(self, client):
        client._mock_http.post_form.return_value = _mock_response(_DOCUMENT_RESPONSE)

        client.update_properties("repo1", "doc-xyz", {"cmis:name": "X"}, change_token="tok-123")

        data = client._mock_http.post_form.call_args[1]["data"]
        assert data["changeToken"] == "tok-123"

    def test_no_change_token_by_default(self, client):
        client._mock_http.post_form.return_value = _mock_response(_DOCUMENT_RESPONSE)

        client.update_properties("repo1", "doc-xyz", {"cmis:name": "X"})

        data = client._mock_http.post_form.call_args[1]["data"]
        assert "changeToken" not in data

    def test_multiple_properties(self, client):
        client._mock_http.post_form.return_value = _mock_response(_DOCUMENT_RESPONSE)

        client.update_properties("repo1", "doc-xyz", {
            "cmis:name": "New",
            "cmis:description": "Desc",
        })

        data = client._mock_http.post_form.call_args[1]["data"]
        assert data["propertyId[0]"] == "cmis:name"
        assert data["propertyValue[0]"] == "New"
        assert data["propertyId[1]"] == "cmis:description"
        assert data["propertyValue[1]"] == "Desc"

    def test_with_tenant_and_user_claim(self, client):
        client._mock_http.post_form.return_value = _mock_response(_DOCUMENT_RESPONSE)
        claim = UserClaim(x_ecm_user_enc="charlie@sap.com")

        client.update_properties("repo1", "doc-xyz", {"cmis:name": "X"}, tenant="t1", user_claim=claim)

        call_args = client._mock_http.post_form.call_args
        assert call_args[1]["tenant_subdomain"] == "t1"
        assert call_args[1]["user_claim"] is claim


# ---------------------------------------------------------------
# get_children
# ---------------------------------------------------------------

_CHILDREN_RESPONSE = {
    "objects": [
        {
            "object": {
                "succinctProperties": {
                    "cmis:objectId": "child-folder-1",
                    "cmis:name": "SubFolder",
                    "cmis:baseTypeId": "cmis:folder",
                    "cmis:objectTypeId": "cmis:folder",
                }
            }
        },
        {
            "object": {
                "succinctProperties": {
                    "cmis:objectId": "child-doc-1",
                    "cmis:name": "readme.txt",
                    "cmis:baseTypeId": "cmis:document",
                    "cmis:objectTypeId": "cmis:document",
                    "cmis:contentStreamLength": 512,
                    "cmis:contentStreamMimeType": "text/plain",
                }
            }
        },
    ],
    "hasMoreItems": True,
    "numItems": 42,
}


class TestGetChildren:
    def test_basic(self, client):
        client._mock_http.get.return_value = _mock_response(_CHILDREN_RESPONSE)

        page = client.get_children("repo1", "root-folder-id")

        assert isinstance(page, ChildrenPage)
        assert len(page.objects) == 2
        assert page.has_more_items is True
        assert page.num_items == 42

        # First child is Folder
        assert isinstance(page.objects[0], Folder)
        assert page.objects[0].object_id == "child-folder-1"

        # Second child is Document
        assert isinstance(page.objects[1], Document)
        assert page.objects[1].object_id == "child-doc-1"

        call_args = client._mock_http.get.call_args
        assert call_args[0][0] == "/browser/repo1/root"
        params = call_args[1]["params"]
        assert params["objectId"] == "root-folder-id"
        assert params["cmisselector"] == "children"
        assert params["maxItems"] == "100"
        assert params["skipCount"] == "0"
        assert params["succinct"] == "true"

    def test_pagination_params(self, client):
        client._mock_http.get.return_value = _mock_response({"objects": [], "hasMoreItems": False})

        client.get_children("repo1", "fid", max_items=50, skip_count=200)

        params = client._mock_http.get.call_args[1]["params"]
        assert params["maxItems"] == "50"
        assert params["skipCount"] == "200"

    def test_with_order_by(self, client):
        client._mock_http.get.return_value = _mock_response({"objects": [], "hasMoreItems": False})

        client.get_children("repo1", "fid", order_by="cmis:creationDate ASC")

        params = client._mock_http.get.call_args[1]["params"]
        assert params["orderBy"] == "cmis:creationDate ASC"

    def test_with_filter(self, client):
        client._mock_http.get.return_value = _mock_response({"objects": [], "hasMoreItems": False})

        client.get_children("repo1", "fid", filter="cmis:name,cmis:objectId")

        params = client._mock_http.get.call_args[1]["params"]
        assert params["filter"] == "cmis:name,cmis:objectId"

    def test_with_include_allowable_and_path_segment(self, client):
        client._mock_http.get.return_value = _mock_response({"objects": [], "hasMoreItems": False})

        client.get_children("repo1", "fid", include_allowable_actions=True, include_path_segment=True)

        params = client._mock_http.get.call_args[1]["params"]
        assert params["includeAllowableActions"] == "true"
        assert params["includePathSegment"] == "true"

    def test_no_optional_params_omitted(self, client):
        client._mock_http.get.return_value = _mock_response({"objects": [], "hasMoreItems": False})

        client.get_children("repo1", "fid")

        params = client._mock_http.get.call_args[1]["params"]
        assert "orderBy" not in params
        assert "filter" not in params
        assert "includeAllowableActions" not in params
        assert "includePathSegment" not in params

    def test_empty_children(self, client):
        client._mock_http.get.return_value = _mock_response({"objects": [], "hasMoreItems": False, "numItems": 0})

        page = client.get_children("repo1", "fid")

        assert page.objects == []
        assert page.has_more_items is False
        assert page.num_items == 0

    def test_with_tenant_and_user_claim(self, client):
        client._mock_http.get.return_value = _mock_response({"objects": [], "hasMoreItems": False})
        claim = UserClaim(x_ecm_user_enc="dana@sap.com")

        client.get_children("repo1", "fid", tenant="t1", user_claim=claim)

        call_args = client._mock_http.get.call_args
        assert call_args[1]["tenant_subdomain"] == "t1"
        assert call_args[1]["user_claim"] is claim
