"""Locks the ratified GeneFoundry Response-Envelope Standard v1 (flat-banner
contract) at this backend's MCP wrapper boundary (``strchive_link.mcp.envelope``).

Adapted from clingen-link (fleet exemplar, PR #20:
https://github.com/berntpopp/clingen-link/pull/20) for this repo's actual
envelope implementation.

Ground truth vs the task-brief assumption: strchive-link does NOT use a separate
``mcp/errors.py`` + ``build_meta`` pattern. Both success ``_meta`` injection
and the flat error envelope are built inline in ``strchive_link/mcp/envelope.py``
via :func:`strchive_link.mcp.envelope.run_mcp_tool` (success path) and the
module-private ``_error_envelope`` (failure path, exercised here indirectly
through ``run_mcp_tool`` -- the only way a tool body's exception becomes a
client-facing envelope). This is architecturally the *same* run_mcp_tool
pattern as clingen-link, not the build_meta pattern described in the task
brief; there is nothing named ``build_meta`` anywhere in this repository.

Fleet decision (2026-07-03): ``_meta.unsafe_for_clinical_use`` must appear on
EVERY tool response -- success AND error, at all response_modes -- not once
via ``get_server_capabilities``. strchive-link now stamps that key on every
per-call ``_meta`` dict (see ``mcp/envelope.py``); the static
``research_use_only`` / ``research_use_notice`` fields in
``get_server_capabilities`` remain the source of the full disclaimer text and
citation/release provenance, which are still declared once to conserve
tokens -- see ``provenance_policy`` / ``per_call_meta`` in
``mcp/capabilities.py``.
"""

from __future__ import annotations

from strchive_link.exceptions import DataUnavailableError, NotFoundError
from strchive_link.mcp.capabilities import build_capabilities
from strchive_link.mcp.envelope import McpErrorContext, run_mcp_tool


async def test_success_envelope_is_flat_with_lean_meta() -> None:
    """SUCCESS: {"success": True, <payload>, "_meta": {...}}, flat (no nesting).

    strchive-link's per-call ``_meta`` carries ``tool``, ``request_id``,
    ``unsafe_for_clinical_use`` (plus optional ``next_commands`` /
    ``argument_aliases_applied`` when a tool body supplies them). See module
    docstring.
    """

    async def call() -> dict[str, object]:
        return {"locus_id": "HD_HTT", "gene": "HTT"}

    result = await run_mcp_tool("get_locus", call, context=McpErrorContext("get_locus"))

    assert result["success"] is True
    assert result["locus_id"] == "HD_HTT"
    assert result["gene"] == "HTT"
    assert result["_meta"]["tool"] == "get_locus"
    assert isinstance(result["_meta"]["request_id"], str)
    assert result["_meta"]["request_id"]
    # Fleet Response-Envelope Standard v1 (2026-07-03): every success envelope
    # stamps the clinical-safety disclaimer per-call.
    assert result["_meta"]["unsafe_for_clinical_use"] is True


async def test_error_envelope_is_flat_never_nested_and_never_raises() -> None:
    """FAILURE: flat in-band dict, NEVER a bare exception, NEVER nested error{}.

    run_mcp_tool is the sole boundary that converts a raised exception into a
    client-facing envelope; asserting on its return value (rather than
    catching an exception) is itself part of the contract -- the exception
    must never escape to the caller.
    """

    async def call() -> dict[str, object]:
        raise NotFoundError()

    result = await run_mcp_tool(
        "get_locus", call, context=McpErrorContext("get_locus", arguments={"query": "ZZZZZ"})
    )

    # Response-Envelope v1: an error now returns a ToolResult(is_error=True) so the
    # MCP `isError` flag is set; the flat envelope rides in structured_content.
    assert result.is_error is True
    env = result.structured_content
    assert env["success"] is False
    assert env["error_code"] == "not_found"
    assert isinstance(env["message"], str)
    assert env["message"]
    assert env["retryable"] is False
    assert isinstance(env["recovery_action"], str)
    assert env["recovery_action"]
    assert "error" not in env
    assert env["_meta"]["tool"] == "get_locus"
    # Fleet Response-Envelope Standard v1 (2026-07-03): error envelopes stamp
    # the clinical-safety disclaimer per-call too, not just on success.
    assert env["_meta"]["unsafe_for_clinical_use"] is True


async def test_error_envelope_flags_retryable_codes_true() -> None:
    """Retryable error classes (e.g. rate_limited) set retryable: True."""

    async def call() -> dict[str, object]:
        raise DataUnavailableError()

    result = await run_mcp_tool("get_locus", call, context=McpErrorContext("get_locus"))

    assert result.is_error is True
    env = result.structured_content
    assert env["success"] is False
    assert env["error_code"] == "upstream_unavailable"
    assert env["retryable"] is True
    assert "error" not in env
    assert env["_meta"]["tool"] == "get_locus"
    assert env["_meta"]["unsafe_for_clinical_use"] is True


def test_research_use_disclaimer_is_declared_once_in_capabilities() -> None:
    """The static disclaimer text/citation/release info still lives here too.

    strchive-link declares ``research_use_only`` / ``research_use_notice``
    (full text + citation + data pin) exactly once in
    ``get_server_capabilities`` to conserve tokens; the machine-checkable
    ``unsafe_for_clinical_use`` flag is additionally stamped on every
    per-call ``_meta`` (see the success/error envelope tests above) and is
    documented here via ``per_call_meta``.
    """
    caps = build_capabilities()

    assert caps["research_use_only"] is True
    assert caps["research_use_notice"]
    assert caps["per_call_meta"] == [
        "tool",
        "request_id",
        "elapsed_ms",
        "source",
        "data_version",
        "next_commands",
        "unsafe_for_clinical_use",
    ]
