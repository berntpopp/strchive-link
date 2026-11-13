"""Tests for argument ergonomics (aliases, did-you-mean, signatures)."""

from __future__ import annotations

from strchive_link.mcp.arg_help import (
    describe_constraints,
    did_you_mean,
    normalize_alias_args,
    tool_signature,
)


def test_normalize_alias_applies_only_for_real_params() -> None:
    new, applied = normalize_alias_args(["locus", "response_mode"], {"gene_symbol": "HTT"})
    assert new == {"locus": "HTT"}
    assert applied == [("gene_symbol", "locus")]


def test_explicit_canonical_wins_over_alias() -> None:
    new, applied = normalize_alias_args(["locus"], {"gene": "X", "locus": "Y"})
    assert new == {"locus": "Y"}
    assert applied == []  # alias dropped, no rewrite recorded


def test_alias_ignored_when_canonical_not_a_param() -> None:
    new, applied = normalize_alias_args(["query", "limit"], {"gene": "X"})
    assert new == {"gene": "X"}  # locus is not a param of this tool
    assert applied == []


def test_did_you_mean_alias_then_fuzzy() -> None:
    assert did_you_mean("gene", ["locus", "response_mode"]) == "locus"
    assert did_you_mean("querie", ["query", "limit"]) == "query"
    assert did_you_mean("zzz", ["query"]) is None


def test_tool_signature_orders_required_first() -> None:
    schema = {"properties": {"query": {}, "response_mode": {}}, "required": ["query"]}
    assert tool_signature("get_locus", schema) == "get_locus(query, response_mode=)"


def test_describe_constraints_enum() -> None:
    result = describe_constraints({"enum": ["a", "b", "c"], "type": "string"})
    assert result is not None
    allowed, human = result
    assert allowed == ["a", "b", "c"]
    assert "one of" in human


def test_describe_constraints_range() -> None:
    result = describe_constraints({"type": "integer", "minimum": 1, "maximum": 200})
    assert result is not None
    allowed, human = result
    assert allowed == ["1..200"]
    assert "between 1 and 200" in human


def test_describe_constraints_none_for_plain() -> None:
    assert describe_constraints({"type": "string"}) is None


def test_float_for_int_names_the_type_not_the_range() -> None:
    schema = {"type": "integer", "minimum": 0, "maximum": 1_000_000}
    assert describe_constraints(schema, "int_from_float") == (
        ["0..1000000"],
        "must be an integer",
    )


def test_string_length_error_describes_the_length() -> None:
    schema = {"type": "string", "minLength": 1, "maxLength": 64}
    assert describe_constraints(schema, "string_too_short") == (
        ["1..64 chars"],
        "must be between 1 and 64 characters long",
    )
