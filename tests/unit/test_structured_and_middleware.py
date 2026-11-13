"""Structured-output declaration and argument-middleware behaviour."""

from __future__ import annotations

from typing import Any


async def test_no_tool_publishes_output_schema(facade: Any) -> None:
    """Tool-Surface Budget Standard v1: outputSchema is suppressed (~40% of the surface).

    Suppression does NOT drop structuredContent -- every tool returns a dict envelope,
    which FastMCP still serialises (see test_structured_content_and_textcontent_fallback).
    """
    tools = await facade.list_tools()
    assert tools
    assert all(t.output_schema is None for t in tools)


async def test_structured_content_and_textcontent_fallback(facade: Any) -> None:
    res = await facade.call_tool("get_locus", {"locus": "HTT"})
    assert isinstance(res.structured_content, dict)
    assert res.content and res.content[0].text  # back-compat JSON block


async def test_bad_arg_name_returns_invalid_input(facade: Any, structured: Any) -> None:
    payload = structured(await facade.call_tool("get_locus", {"locs": "HTT"}))
    assert payload["success"] is False
    assert payload["error_code"] == "invalid_input"
    assert payload["field"] == "locus"  # missing required after alias miss
    assert "get_locus(" in payload["hint"]
    assert payload["_meta"]["next_commands"][0]["tool"] == "get_server_capabilities"


async def test_unknown_arg_suggests_canonical(facade: Any, structured: Any) -> None:
    payload = structured(
        await facade.call_tool("get_locus", {"locus": "HTT", "respons_mode": "full"})
    )
    assert payload["error_code"] == "invalid_input"
    assert payload["field"] == "respons_mode"
    assert "response_mode" in (payload["message"] + str(payload.get("hint", "")))
