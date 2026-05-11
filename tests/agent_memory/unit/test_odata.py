"""Unit tests for OData query-building utilities."""

from sap_cloud_sdk.agent_memory.utils._odata import (
    FilterDefinition,
    _escape_odata_string,
    build_contains_clauses,
    build_list_params,
    build_memory_filter,
    build_message_filter,
    extract_value_and_count,
)


# ── _escape_odata_string ──────────────────────────────────────────────────────


class TestEscapeOdataString:

    def test_single_quote_is_doubled(self):
        """Single quotes are escaped as '' per OData 4.01."""
        assert _escape_odata_string("it's") == "it''s"

    def test_multiple_single_quotes(self):
        """All single quotes in the value are escaped."""
        assert _escape_odata_string("a'b'c") == "a''b''c"

    def test_no_quotes_unchanged(self):
        """Values without single quotes are returned unchanged."""
        assert _escape_odata_string("john") == "john"

    def test_empty_string(self):
        """Empty string is returned unchanged."""
        assert _escape_odata_string("") == ""


# ── build_contains_clauses ────────────────────────────────────────────────────


class TestBuildContainsClauses:

    def test_single_clause(self):
        """A single clause produces one contains() expression."""
        result = build_contains_clauses([FilterDefinition(target="metadata", contains="john")])
        assert result == ["contains(metadata, 'john')"]

    def test_multiple_clauses(self):
        """Multiple clauses produce one expression per clause."""
        result = build_contains_clauses([
            FilterDefinition(target="metadata", contains="john"),
            FilterDefinition(target="content", contains="user prefers"),
        ])
        assert result == [
            "contains(metadata, 'john')",
            "contains(content, 'user prefers')",
        ]

    def test_single_quote_in_value_is_escaped(self):
        """Single quotes inside the contains value are escaped."""
        result = build_contains_clauses([FilterDefinition(target="content", contains="it's")])
        assert result == ["contains(content, 'it''s')"]

    def test_empty_clause_list_returns_empty_list(self):
        """An empty input list returns an empty list."""
        assert build_contains_clauses([]) == []


# ── build_memory_filter ──────────────────────────────────────────────────────


class TestBuildMemoryFilter:

    def test_agent_id_only(self):
        """Single agent_id produces a simple eq filter."""
        result = build_memory_filter(agent_id="agent-a")
        assert result == "agentID eq 'agent-a'"

    def test_invoker_id_only(self):
        """Single invoker_id produces a simple eq filter."""
        result = build_memory_filter(invoker_id="user-b")
        assert result == "invokerID eq 'user-b'"

    def test_both_filters(self):
        """Both filters are combined with 'and'."""
        result = build_memory_filter(agent_id="a", invoker_id="u")
        assert result is not None
        assert "agentID eq 'a'" in result
        assert "invokerID eq 'u'" in result
        assert " and " in result

    def test_no_filters_returns_none(self):
        """No arguments returns None."""
        result = build_memory_filter()
        assert result is None

    def test_filter_clauses_appended(self):
        """FilterDefinition objects are appended as contains() expressions."""
        result = build_memory_filter(
            agent_id="a",
            filter_clauses=[FilterDefinition(target="content", contains="dark mode")],
        )
        assert result is not None
        assert "agentID eq 'a'" in result
        assert "contains(content, 'dark mode')" in result
        assert " and " in result

    def test_agent_id_with_single_quote_is_escaped(self):
        """Single quotes in agent_id are escaped to prevent malformed OData."""
        result = build_memory_filter(agent_id="bob's-agent")
        assert result == "agentID eq 'bob''s-agent'"

    def test_invoker_id_with_single_quote_is_escaped(self):
        """Single quotes in invoker_id are escaped."""
        result = build_memory_filter(invoker_id="o'brien")
        assert result == "invokerID eq 'o''brien'"


# ── build_message_filter ─────────────────────────────────────────────────────


class TestBuildMessageFilter:

    def test_all_filters(self):
        """All four message filters are combined."""
        result = build_message_filter(
            agent_id="a", invoker_id="u",
            message_group="g", role="USER",
        )
        assert result is not None
        assert "agentID eq 'a'" in result
        assert "invokerID eq 'u'" in result
        assert "messageGroup eq 'g'" in result
        assert "role eq 'USER'" in result

    def test_single_filter(self):
        """A single filter produces a simple eq expression."""
        result = build_message_filter(role="ASSISTANT")
        assert result == "role eq 'ASSISTANT'"

    def test_no_filters_returns_none(self):
        """No arguments returns None."""
        result = build_message_filter()
        assert result is None

    def test_filter_clauses_appended(self):
        """FilterDefinition objects are appended as contains() expressions."""
        result = build_message_filter(
            agent_id="a",
            filter_clauses=[FilterDefinition(target="content", contains="invoice")],
        )
        assert result is not None
        assert "agentID eq 'a'" in result
        assert "contains(content, 'invoice')" in result
        assert " and " in result

    def test_agent_id_with_single_quote_is_escaped(self):
        """Single quotes in agent_id are escaped to prevent malformed OData."""
        result = build_message_filter(agent_id="bob's-agent")
        assert result == "agentID eq 'bob''s-agent'"

    def test_invoker_id_with_single_quote_is_escaped(self):
        """Single quotes in invoker_id are escaped."""
        result = build_message_filter(invoker_id="user-x'y")
        assert result == "invokerID eq 'user-x''y'"

    def test_message_group_with_single_quote_is_escaped(self):
        """Single quotes in message_group are escaped."""
        result = build_message_filter(message_group="group'1")
        assert result == "messageGroup eq 'group''1'"

    def test_role_with_single_quote_is_escaped(self):
        """Single quotes in role are escaped."""
        result = build_message_filter(role="US'ER")
        assert result == "role eq 'US''ER'"


# ── build_list_params ────────────────────────────────────────────────────────


class TestBuildListParams:

    def test_filter_param(self):
        """filter_expr is output as $filter."""
        params = build_list_params(filter_expr="agentID eq 'a'")
        assert params["$filter"] == "agentID eq 'a'"

    def test_search_param(self):
        """search is output as $search."""
        params = build_list_params(search="dark mode")
        assert params["$search"] == "dark mode"

    def test_select_param_injects_required_fields(self):
        """$select always includes agentID and invokerID."""
        params = build_list_params(select="id,content")
        fields = set(params["$select"].split(","))
        assert "id" in fields
        assert "content" in fields
        assert "agentID" in fields
        assert "invokerID" in fields

    def test_select_param_no_duplicates(self):
        """$select does not duplicate agentID/invokerID if already present."""
        params = build_list_params(select="agentID,invokerID,content")
        fields = params["$select"].split(",")
        assert fields.count("agentID") == 1
        assert fields.count("invokerID") == 1

    def test_top_param(self):
        """top is output as $top string."""
        params = build_list_params(top=10)
        assert params["$top"] == "10"

    def test_skip_param(self):
        """skip is output as $skip string."""
        params = build_list_params(skip=20)
        assert params["$skip"] == "20"

    def test_order_by_param(self):
        """order_by is output as $orderby."""
        params = build_list_params(order_by="createTimestamp desc")
        assert params["$orderby"] == "createTimestamp desc"

    def test_count_true(self):
        """count=True outputs $count=true."""
        params = build_list_params(count=True)
        assert params["$count"] == "true"

    def test_count_false(self):
        """count=False omits $count."""
        params = build_list_params(count=False)
        assert "$count" not in params

    def test_empty_params(self):
        """No arguments produces an empty dict."""
        params = build_list_params()
        assert params == {}

    def test_all_params(self):
        """All parameters are set in a single call."""
        params = build_list_params(
            filter_expr="agentID eq 'a'",
            search="hello",
            select="id,content",
            top=5,
            skip=10,
            order_by="createTimestamp desc",
            count=True,
        )
        assert params["$filter"] == "agentID eq 'a'"
        assert params["$search"] == "hello"
        assert "id" in params["$select"]
        assert params["$top"] == "5"
        assert params["$skip"] == "10"
        assert params["$orderby"] == "createTimestamp desc"
        assert params["$count"] == "true"


# ── extract_value_and_count ──────────────────────────────────────────────────


class TestExtractValueAndCount:

    def test_data_format(self):
        """Parses the 'data' + 'count' response format."""
        response = {
            "data": [{"id": "1"}, {"id": "2"}],
            "count": 42,
        }
        items, total = extract_value_and_count(response)
        assert len(items) == 2
        assert total == 42

    def test_odata_value_format(self):
        """Parses the OData 'value' + '@odata.count' response format."""
        response = {
            "value": [{"id": "1"}],
            "@odata.count": 10,
        }
        items, total = extract_value_and_count(response)
        assert len(items) == 1
        assert total == 10

    def test_odata_count_key(self):
        """Parses the OData '@count' response format (alternative to '@odata.count')."""
        response = {
            "value": [{"id": "1"}],
            "@count": 7,
        }
        items, total = extract_value_and_count(response)
        assert len(items) == 1
        assert total == 7

    def test_value_takes_precedence_over_data(self):
        """When both 'value' and 'data' are present, 'value' wins (OData v4 standard)."""
        response = {
            "data": [{"id": "from-data"}],
            "value": [{"id": "from-value"}],
        }
        items, _ = extract_value_and_count(response)
        assert items[0]["id"] == "from-value"

    def test_missing_count_returns_none(self):
        """Missing count keys return None."""
        response = {"data": []}
        _, total = extract_value_and_count(response)
        assert total is None

    def test_empty_response(self):
        """Empty dict returns empty list and None count."""
        items, total = extract_value_and_count({})
        assert items == []
        assert total is None
