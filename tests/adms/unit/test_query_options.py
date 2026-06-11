"""Unit tests for ADMS OData query option classes."""

from dataclasses import is_dataclass

import pytest

from sap_cloud_sdk.adms._query_options import (
    ConfigQueryOptions,
    DocumentQueryOptions,
    RelationQueryOptions,
)


class TestConfigQueryOptions:
    def test_is_dataclass(self):
        assert is_dataclass(ConfigQueryOptions)

    def test_empty_options_yield_empty_params(self):
        assert ConfigQueryOptions().to_query_params() == {}

    def test_filter_only(self):
        params = ConfigQueryOptions(filter="Name eq 'PDF'").to_query_params()
        assert params == {"$filter": "Name eq 'PDF'"}

    def test_top_only(self):
        params = ConfigQueryOptions(top=10).to_query_params()
        assert params == {"$top": 10}

    def test_skip_only(self):
        params = ConfigQueryOptions(skip=20).to_query_params()
        assert params == {"$skip": 20}

    def test_all_fields_together(self):
        params = ConfigQueryOptions(filter="x", top=5, skip=2).to_query_params()
        assert params == {"$filter": "x", "$top": 5, "$skip": 2}


class TestRelationQueryOptions:
    def test_is_dataclass(self):
        assert is_dataclass(RelationQueryOptions)

    def test_inherits_from_config(self):
        # Composition behaviour: RelationQueryOptions accepts every Config field.
        assert issubclass(RelationQueryOptions, ConfigQueryOptions)

    def test_empty_options_yield_empty_params(self):
        assert RelationQueryOptions().to_query_params() == {}

    def test_select_is_comma_joined(self):
        params = RelationQueryOptions(select=["A", "B", "C"]).to_query_params()
        assert params == {"$select": "A,B,C"}

    def test_expand_is_comma_joined(self):
        params = RelationQueryOptions(expand=["Document", "Lock"]).to_query_params()
        assert params == {"$expand": "Document,Lock"}

    def test_select_single_value_no_trailing_comma(self):
        params = RelationQueryOptions(select=["Only"]).to_query_params()
        assert params == {"$select": "Only"}

    def test_inherits_filter_top_skip(self):
        # Inherited fields must produce the same keys as ConfigQueryOptions.
        params = RelationQueryOptions(filter="x", top=5, skip=2).to_query_params()
        assert params == {"$filter": "x", "$top": 5, "$skip": 2}

    def test_all_fields_together(self):
        params = RelationQueryOptions(
            filter="x",
            top=5,
            skip=2,
            select=["A", "B"],
            expand=["Document"],
        ).to_query_params()
        assert params == {
            "$filter": "x",
            "$top": 5,
            "$skip": 2,
            "$select": "A,B",
            "$expand": "Document",
        }

    def test_orderby_not_accepted(self):
        # $orderby is reserved for DocumentQueryOptions — RelationQueryOptions
        # must not silently accept it as a kwarg.
        with pytest.raises(TypeError):
            RelationQueryOptions(orderby="CreatedAt desc")  # type: ignore[call-arg]  # ty: ignore[unknown-argument]


class TestDocumentQueryOptions:
    def test_is_dataclass(self):
        assert is_dataclass(DocumentQueryOptions)

    def test_inherits_from_relation(self):
        assert issubclass(DocumentQueryOptions, RelationQueryOptions)
        # Transitively also a ConfigQueryOptions.
        assert issubclass(DocumentQueryOptions, ConfigQueryOptions)

    def test_empty_options_yield_empty_params(self):
        assert DocumentQueryOptions().to_query_params() == {}

    def test_orderby_only(self):
        params = DocumentQueryOptions(orderby="CreatedAt desc").to_query_params()
        assert params == {"$orderby": "CreatedAt desc"}

    def test_inherits_select_and_expand(self):
        params = DocumentQueryOptions(
            select=["A"], expand=["Document"]
        ).to_query_params()
        assert params == {"$select": "A", "$expand": "Document"}

    def test_full_six_param_surface(self):
        params = DocumentQueryOptions(
            filter="DocumentName eq 'Invoice.pdf'",
            select=["DocumentID", "DocumentName"],
            expand=["Document"],
            top=10,
            skip=5,
            orderby="CreatedAt desc",
        ).to_query_params()
        assert params == {
            "$filter": "DocumentName eq 'Invoice.pdf'",
            "$select": "DocumentID,DocumentName",
            "$expand": "Document",
            "$top": 10,
            "$skip": 5,
            "$orderby": "CreatedAt desc",
        }


class TestInheritanceConsistency:
    """Cross-class checks: same input field → same output key, regardless of class."""

    def test_filter_key_consistent_across_classes(self):
        cfg = ConfigQueryOptions(filter="x").to_query_params()
        rel = RelationQueryOptions(filter="x").to_query_params()
        doc = DocumentQueryOptions(filter="x").to_query_params()
        assert cfg == rel == doc == {"$filter": "x"}

    def test_top_skip_keys_consistent(self):
        cfg = ConfigQueryOptions(top=5, skip=2).to_query_params()
        rel = RelationQueryOptions(top=5, skip=2).to_query_params()
        doc = DocumentQueryOptions(top=5, skip=2).to_query_params()
        assert cfg == rel == doc == {"$top": 5, "$skip": 2}
