"""Unit tests for CMIS object models."""

from datetime import datetime, timezone


from sap_cloud_sdk.dms.model import (
    Ace,
    Acl,
    ChildrenPage,
    CmisObject,
    Document,
    Folder,
    _parse_datetime as _parse_cmis_datetime,
    _prop_val,
)


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------


class TestParseCmisDatetime:
    def test_none_returns_none(self):
        assert _parse_cmis_datetime(None) is None

    def test_epoch_millis(self):
        # 2024-01-15T12:00:00Z
        result = _parse_cmis_datetime(1705320000000)
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
        assert result.year == 2024

    def test_iso_string_with_z(self):
        result = _parse_cmis_datetime("2024-01-15T12:00:00Z")
        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_iso_string_with_offset(self):
        result = _parse_cmis_datetime("2024-01-15T12:00:00+00:00")
        assert isinstance(result, datetime)


class TestPropVal:
    def test_succinct_format(self):
        props = {"cmis:name": "MyDoc"}
        assert _prop_val(props, "cmis:name") == "MyDoc"

    def test_verbose_format(self):
        props = {"cmis:name": {"value": "MyDoc"}}
        assert _prop_val(props, "cmis:name") == "MyDoc"

    def test_missing_key_returns_none(self):
        assert _prop_val({}, "cmis:name") is None

    def test_dict_without_value_key(self):
        props = {"cmis:name": {"id": "cmis:name", "localName": "name"}}
        result = _prop_val(props, "cmis:name")
        assert isinstance(result, dict)

    def test_boolean_value(self):
        props = {"cmis:isLatestVersion": True}
        assert _prop_val(props, "cmis:isLatestVersion") is True

    def test_integer_value(self):
        props = {"cmis:contentStreamLength": 42}
        assert _prop_val(props, "cmis:contentStreamLength") == 42


# ---------------------------------------------------------------
# CmisObject
# ---------------------------------------------------------------

_SUCCINCT_FOLDER = {
    "succinctProperties": {
        "cmis:objectId": "folder-123",
        "cmis:name": "TestFolder",
        "cmis:baseTypeId": "cmis:folder",
        "cmis:objectTypeId": "cmis:folder",
        "cmis:createdBy": "admin",
        "cmis:creationDate": 1705320000000,
        "cmis:lastModifiedBy": "admin",
        "cmis:lastModificationDate": 1705320000000,
        "cmis:changeToken": "tok1",
        "cmis:description": "A test folder",
        "sap:parentIds": ["root-id"],
    }
}

_SUCCINCT_DOCUMENT = {
    "succinctProperties": {
        "cmis:objectId": "doc-456",
        "cmis:name": "readme.txt",
        "cmis:baseTypeId": "cmis:document",
        "cmis:objectTypeId": "cmis:document",
        "cmis:createdBy": "user1",
        "cmis:creationDate": 1705320000000,
        "cmis:lastModifiedBy": "user1",
        "cmis:lastModificationDate": 1705320000000,
        "cmis:contentStreamLength": 1024,
        "cmis:contentStreamMimeType": "text/plain",
        "cmis:contentStreamFileName": "readme.txt",
        "cmis:versionSeriesId": "vs-789",
        "cmis:versionLabel": "1.0",
        "cmis:isLatestVersion": True,
        "cmis:isMajorVersion": True,
        "cmis:isLatestMajorVersion": True,
        "cmis:isPrivateWorkingCopy": False,
        "cmis:checkinComment": "Initial upload",
        "cmis:isVersionSeriesCheckedOut": False,
        "cmis:versionSeriesCheckedOutId": None,
        "sap:parentIds": ["folder-123"],
    }
}


class TestCmisObject:
    def test_from_dict_succinct(self):
        obj = CmisObject.from_dict(_SUCCINCT_FOLDER)
        assert obj.object_id == "folder-123"
        assert obj.name == "TestFolder"
        assert obj.base_type_id == "cmis:folder"
        assert obj.created_by == "admin"
        assert obj.description == "A test folder"
        assert obj.parent_ids == ["root-id"]
        assert isinstance(obj.creation_date, datetime)

    def test_from_dict_verbose(self):
        data = {
            "properties": {
                "cmis:objectId": {"value": "obj-99"},
                "cmis:name": {"value": "VerboseObj"},
                "cmis:baseTypeId": {"value": "cmis:folder"},
                "cmis:objectTypeId": {"value": "cmis:folder"},
            }
        }
        obj = CmisObject.from_dict(data)
        assert obj.object_id == "obj-99"
        assert obj.name == "VerboseObj"

    def test_from_dict_empty(self):
        obj = CmisObject.from_dict({})
        assert obj.object_id == ""
        assert obj.name == ""
        assert obj.properties == {}

    def test_from_dict_prefers_succinct_over_properties(self):
        data = {
            "succinctProperties": {"cmis:name": "Succinct"},
            "properties": {"cmis:name": {"value": "Verbose"}},
        }
        obj = CmisObject.from_dict(data)
        assert obj.name == "Succinct"


# ---------------------------------------------------------------
# Folder
# ---------------------------------------------------------------


class TestFolder:
    def test_from_dict(self):
        folder = Folder.from_dict(_SUCCINCT_FOLDER)
        assert isinstance(folder, Folder)
        assert isinstance(folder, CmisObject)
        assert folder.object_id == "folder-123"
        assert folder.name == "TestFolder"

    def test_from_dict_empty(self):
        folder = Folder.from_dict({})
        assert folder.object_id == ""


# ---------------------------------------------------------------
# Document
# ---------------------------------------------------------------


class TestDocument:
    def test_from_dict_full(self):
        doc = Document.from_dict(_SUCCINCT_DOCUMENT)
        assert isinstance(doc, Document)
        assert isinstance(doc, CmisObject)
        assert doc.object_id == "doc-456"
        assert doc.name == "readme.txt"
        assert doc.content_stream_length == 1024
        assert doc.content_stream_mime_type == "text/plain"
        assert doc.content_stream_file_name == "readme.txt"
        assert doc.version_series_id == "vs-789"
        assert doc.version_label == "1.0"
        assert doc.is_latest_version is True
        assert doc.is_major_version is True
        assert doc.is_latest_major_version is True
        assert doc.is_private_working_copy is False
        assert doc.checkin_comment == "Initial upload"
        assert doc.is_version_series_checked_out is False
        assert doc.version_series_checked_out_id is None
        assert doc.parent_ids == ["folder-123"]

    def test_from_dict_minimal(self):
        data = {
            "succinctProperties": {
                "cmis:objectId": "doc-min",
                "cmis:name": "minimal.pdf",
                "cmis:baseTypeId": "cmis:document",
                "cmis:objectTypeId": "cmis:document",
            }
        }
        doc = Document.from_dict(data)
        assert doc.object_id == "doc-min"
        assert doc.content_stream_length is None
        assert doc.version_label is None

    def test_from_dict_empty(self):
        doc = Document.from_dict({})
        assert doc.object_id == ""
        assert doc.content_stream_length is None


# ---------------------------------------------------------------
# Ace
# ---------------------------------------------------------------


class TestAce:
    def test_from_dict(self):
        data = {
            "principal": {"principalId": "user1"},
            "permissions": ["cmis:read", "cmis:write"],
            "isDirect": True,
        }
        ace = Ace.from_dict(data)
        assert ace.principal_id == "user1"
        assert ace.permissions == ["cmis:read", "cmis:write"]
        assert ace.is_direct is True

    def test_from_dict_missing_principal(self):
        ace = Ace.from_dict({})
        assert ace.principal_id == ""
        assert ace.permissions == []
        assert ace.is_direct is True

    def test_from_dict_indirect(self):
        data = {
            "principal": {"principalId": "role:Admin"},
            "permissions": ["cmis:all"],
            "isDirect": False,
        }
        ace = Ace.from_dict(data)
        assert ace.is_direct is False

    def test_constructor(self):
        ace = Ace(principal_id="p1", permissions=["cmis:read"])
        assert ace.principal_id == "p1"
        assert ace.permissions == ["cmis:read"]


# ---------------------------------------------------------------
# Acl
# ---------------------------------------------------------------


class TestAcl:
    def test_from_dict(self):
        data = {
            "aces": [
                {
                    "principal": {"principalId": "user1"},
                    "permissions": ["cmis:read"],
                    "isDirect": True,
                },
                {
                    "principal": {"principalId": "user2"},
                    "permissions": ["cmis:write"],
                    "isDirect": False,
                },
            ],
            "isExact": False,
        }
        acl = Acl.from_dict(data)
        assert len(acl.aces) == 2
        assert acl.aces[0].principal_id == "user1"
        assert acl.aces[1].principal_id == "user2"
        assert acl.is_exact is False

    def test_from_dict_empty(self):
        acl = Acl.from_dict({})
        assert acl.aces == []
        assert acl.is_exact is True

    def test_from_dict_no_aces(self):
        acl = Acl.from_dict({"aces": [], "isExact": True})
        assert acl.aces == []


class TestChildrenPage:
    def test_from_dict_mixed_types(self):
        data = {
            "objects": [
                {
                    "object": {
                        "succinctProperties": {
                            "cmis:objectId": "f1",
                            "cmis:name": "Folder1",
                            "cmis:baseTypeId": "cmis:folder",
                            "cmis:objectTypeId": "cmis:folder",
                        }
                    }
                },
                {
                    "object": {
                        "succinctProperties": {
                            "cmis:objectId": "d1",
                            "cmis:name": "Doc1",
                            "cmis:baseTypeId": "cmis:document",
                            "cmis:objectTypeId": "cmis:document",
                            "cmis:contentStreamLength": 100,
                        }
                    }
                },
            ],
            "hasMoreItems": True,
            "numItems": 50,
        }
        page = ChildrenPage.from_dict(data)
        assert len(page.objects) == 2
        assert isinstance(page.objects[0], Folder)
        assert isinstance(page.objects[1], Document)
        assert page.objects[0].object_id == "f1"
        assert page.objects[1].object_id == "d1"
        assert page.objects[1].content_stream_length == 100
        assert page.has_more_items is True
        assert page.num_items == 50

    def test_from_dict_empty(self):
        page = ChildrenPage.from_dict({"objects": [], "hasMoreItems": False})
        assert page.objects == []
        assert page.has_more_items is False
        assert page.num_items is None

    def test_from_dict_unknown_type(self):
        data = {
            "objects": [
                {
                    "object": {
                        "succinctProperties": {
                            "cmis:objectId": "i1",
                            "cmis:name": "Item",
                            "cmis:baseTypeId": "cmis:item",
                            "cmis:objectTypeId": "cmis:item",
                        }
                    }
                },
            ],
            "hasMoreItems": False,
        }
        page = ChildrenPage.from_dict(data)
        assert len(page.objects) == 1
        assert isinstance(page.objects[0], CmisObject)
        assert not isinstance(page.objects[0], (Folder, Document))

    def test_from_dict_no_num_items(self):
        page = ChildrenPage.from_dict({"objects": [], "hasMoreItems": True})
        assert page.has_more_items is True
        assert page.num_items is None
