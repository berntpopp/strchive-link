"""MCP contract-hardening v1 regression guards (issue #26 + fleet-four).

Locks the four fleet-wide contract fixes at the FastMCP-facade boundary:

* every error envelope carries the protocol ``isError: true`` flag (not just
  ``success: false``), so a client branching on ``isError`` sees the failure;
* ``error_code`` stays inside the closed six-value enum;
* a mistyped argument names the TYPE, not a phantom range (D5).
"""

from __future__ import annotations

from typing import Any

import pytest

# The exact six-value error_code enum (Response-Envelope Standard v1).
ERROR_CODES = {
    "invalid_input",
    "not_found",
    "ambiguous_query",
    "upstream_unavailable",
    "rate_limited",
    "internal",
}


@pytest.mark.parametrize(
    ("tool", "args"),
    [
        ("get_locus", {"locus": "ZZZZZ"}),  # not_found
        ("get_locus", {"locus": "ARX"}),  # ambiguous_query
        ("get_locus", {"nope": "x"}),  # invalid_input (unknown arg)
        ("get_locus", {"locus": "HTT", "response_mode": "huge"}),  # invalid_input (enum)
        ("search_loci", {"query": "x", "limit": "ten"}),  # invalid_input (bad type)
        ("search_loci", {"query": "x", "limit": 0}),  # invalid_input (range)
        ("compare_repeat_length", {"locus": "HTT"}),  # invalid_input (missing count)
    ],
)
async def test_every_error_sets_is_error_and_a_canon_code(
    facade: Any, structured: Any, tool: str, args: dict[str, Any]
) -> None:
    result = await facade.call_tool(tool, args)
    payload = structured(result)
    assert payload["success"] is False
    # THE fleet fix: a returned error envelope MUST set the protocol isError flag.
    assert result.is_error is True, f"{tool} error envelope did not set isError:true"
    assert payload["error_code"] in ERROR_CODES


async def test_success_call_is_not_flagged_as_error(facade: Any, structured: Any) -> None:
    result = await facade.call_tool("get_locus", {"locus": "HTT"})
    assert result.is_error is False
    assert structured(result)["success"] is True


async def test_mistyped_limit_names_the_type_not_a_range(facade: Any, structured: Any) -> None:
    """D5: limit='ten' is a TYPE error ('must be an integer'), not a range violation."""
    payload = structured(await facade.call_tool("search_loci", {"query": "HTT", "limit": "ten"}))
    assert payload["error_code"] == "invalid_input"
    assert payload["field"] == "limit"
    assert "integer" in payload["message"]
    assert "between" not in payload["message"]


async def test_full_adds_fields_over_standard(facade: Any, structured: Any) -> None:
    """standard and full are not identical for get_locus."""
    standard = structured(
        await facade.call_tool("get_locus", {"locus": "HTT", "response_mode": "standard"})
    )
    full = structured(
        await facade.call_tool("get_locus", {"locus": "HTT", "response_mode": "full"})
    )
    assert "cross_references" in full["result"]
    assert "cross_references" not in standard["result"]
    assert set(full["result"]) > set(standard["result"])
