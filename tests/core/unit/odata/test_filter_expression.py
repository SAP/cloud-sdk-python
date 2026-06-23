"""Unit tests for FilterExpression DSL."""

import pytest
from sap_cloud_sdk.core.odata._filter import FilterExpression, _format_value


class TestFormatValue:
    def test_string_single_quotes(self):
        assert _format_value("hello") == "'hello'"

    def test_string_escapes_embedded_quotes(self):
        assert _format_value("O'Brien") == "'O''Brien'"

    def test_integer(self):
        assert _format_value(42) == "42"

    def test_float(self):
        assert _format_value(3.14) == "3.14"

    def test_bool_true(self):
        assert _format_value(True) == "true"

    def test_bool_false(self):
        assert _format_value(False) == "false"


class TestFieldRef:
    def test_eq_string(self):
        f = FilterExpression.field("Name").eq("Acme")
        assert str(f) == "Name eq 'Acme'"

    def test_ne(self):
        assert str(FilterExpression.field("Status").ne("X")) == "Status ne 'X'"

    def test_lt(self):
        assert str(FilterExpression.field("Price").lt(100)) == "Price lt 100"

    def test_le(self):
        assert str(FilterExpression.field("Price").le(100)) == "Price le 100"

    def test_gt(self):
        assert str(FilterExpression.field("Price").gt(0)) == "Price gt 0"

    def test_ge(self):
        assert str(FilterExpression.field("Price").ge(1)) == "Price ge 1"

    def test_contains(self):
        assert (
            str(FilterExpression.field("Name").contains("Acme"))
            == "contains(Name, 'Acme')"
        )

    def test_starts_with(self):
        assert (
            str(FilterExpression.field("Name").starts_with("A"))
            == "startswith(Name, 'A')"
        )

    def test_ends_with(self):
        assert (
            str(FilterExpression.field("Name").ends_with("Corp"))
            == "endswith(Name, 'Corp')"
        )


class TestFilterExpressionComposition:
    def test_and_(self):
        f = (
            FilterExpression.field("Price")
            .gt(100)
            .and_(FilterExpression.field("Category").eq("Books"))
        )
        assert str(f) == "(Price gt 100) and (Category eq 'Books')"

    def test_or_(self):
        f = (
            FilterExpression.field("Status")
            .eq("A")
            .or_(FilterExpression.field("Status").eq("B"))
        )
        assert str(f) == "(Status eq 'A') or (Status eq 'B')"

    def test_not_(self):
        f = FilterExpression.field("Deleted").eq(True).not_()
        assert str(f) == "not (Deleted eq true)"

    def test_chained_and_or(self):
        f = (
            FilterExpression.field("A")
            .eq(1)
            .and_(FilterExpression.field("B").eq(2))
            .or_(FilterExpression.field("C").eq(3))
        )
        assert str(f) == "((A eq 1) and (B eq 2)) or (C eq 3)"

    def test_equality(self):
        a = FilterExpression.field("X").eq(1)
        b = FilterExpression.field("X").eq(1)
        assert a == b

    def test_hash_consistency(self):
        a = FilterExpression.field("X").eq(1)
        assert hash(a) == hash(FilterExpression.field("X").eq(1))
