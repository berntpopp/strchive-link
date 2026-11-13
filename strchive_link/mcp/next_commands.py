"""Builders for `_meta.next_commands` entries: `{tool, arguments}` steps.

Only grammar-validated identifiers are echoed into a next_command; a free-form
caller value (which could carry injection prose) is never placed into one.
"""

from __future__ import annotations

from typing import Any

from strchive_link.safe_fields import is_locus_key


def cmd(tool: str, **arguments: Any) -> dict[str, Any]:
    """One ready-to-call next step."""
    return {"tool": tool, "arguments": arguments}


def default_error_next_commands(
    tool: str, error_code: str, arguments: dict[str, Any]
) -> list[dict[str, Any]]:
    """A sensible recovery step for any error lacking an explicit fallback."""
    if error_code == "upstream_unavailable":
        return [cmd("get_diagnostics")]
    if tool in ("get_locus", "compare_repeat_length") and error_code == "not_found":
        value = arguments.get("locus")
        if is_locus_key(value):
            return [cmd("search_loci", query=value)]
    return [cmd("get_server_capabilities")]


def after_search(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """After search_loci: open the top hit, or point home if empty."""
    if results and is_locus_key(results[0].get("locus_id")):
        return [cmd("get_locus", locus=results[0]["locus_id"])]
    return [cmd("search_loci"), cmd("get_server_capabilities")]


def after_locus(locus_id: str, gene: str, mode: str) -> list[dict[str, Any]]:
    """After get_locus: the fenced source notes, else the gene's other loci (always executable)."""
    if mode in ("minimal", "compact"):
        return [cmd("get_locus", locus=locus_id, response_mode="standard")]
    return [cmd("search_loci", query=gene)]
