"""Unit tests for StructuredQuery builder."""

import pytest
from sap_cloud_sdk.core.odata._query import OrderDirection, StructuredQuery
from sap_cloud_sdk.core.odata._filter import FilterExpression


class TestStructuredQueryImmutability:
    def test_select_returns_new_instance(self):
        q = StructuredQuery()
        q2 = q.select("A", "B")
        assert q is not q2
        assert q.to_params() == {}
        assert "$select" in q2.to_params()

    def test_chained_calls_do_not_mutate_base(self):
        base = StructuredQuery().top(10)
        page1 = base.skip(0)
        page2 = base.skip(10)
        assert page1.to_params()["$skip"] == "0"
        assert page2.to_params()["$skip"] == "10"
        assert "$skip" not in base.to_params()


class TestToParams:
    def test_empty_query_produces_no_params(self):
        assert StructuredQuery().to_params() == {}

    def test_select(self):
        params = StructuredQuery().select("ID", "Name").to_params()
        assert params["$select"] == "ID,Name"

    def test_top(self):
        assert StructuredQuery().top(20).to_params()["$top"] == "20"

    def test_skip(self):
        assert StructuredQuery().skip(5).to_params()["$skip"] == "5"

    def test_filter(self):
        f = FilterExpression.field("Name").eq("Acme")
        params = StructuredQuery().filter(f).to_params()
        assert params["$filter"] == "Name eq 'Acme'"

    def test_order_by_asc(self):
        params = StructuredQuery().order_by("Name").to_params()
        assert params["$orderby"] == "Name asc"

    def test_order_by_desc(self):
        params = (
            StructuredQuery()
            .order_by("CreatedAt", OrderDirection.DESC)
            .to_params()
        )
        assert params["$orderby"] == "CreatedAt desc"

    def test_multiple_order_by_fields(self):
        params = (
            StructuredQuery()
            .order_by("Name", OrderDirection.ASC)
            .order_by("CreatedAt", OrderDirection.DESC)
            .to_params()
        )
        assert params["$orderby"] == "Name asc,CreatedAt desc"

    def test_expand(self):
        params = StructuredQuery().expand("ToAddresses", "ToOrders").to_params()
        assert params["$expand"] == "ToAddresses,ToOrders"

    def test_custom_param(self):
        params = StructuredQuery().custom("sap-language", "en").to_params()
        assert params["sap-language"] == "en"

    def test_custom_param_overwrite(self):
        q = StructuredQuery().custom("foo", "bar").custom("foo", "baz")
        assert q.to_params()["foo"] == "baz"

    def test_full_query(self):
        f = FilterExpression.field("Name").eq("Acme")
        params = (
            StructuredQuery()
            .select("ID", "Name")
            .filter(f)
            .order_by("Name")
            .top(20)
            .skip(0)
            .expand("ToAddresses")
            .to_params()
        )
        assert params == {
            "$select": "ID,Name",
            "$filter": "Name eq 'Acme'",
            "$orderby": "Name asc",
            "$top": "20",
            "$skip": "0",
            "$expand": "ToAddresses",
        }
