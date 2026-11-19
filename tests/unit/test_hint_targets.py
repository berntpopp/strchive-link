"""Guard: every tool/argument a `_meta.next_commands` step names must really exist.

Checks the literal ``cmd("tool", arg=...)`` templates in the package source (AST scan)
and the steps real responses emit, against the server's live input schemas. A renamed
tool or argument then fails here instead of sending an agent to a dead end.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import strchive_link
from strchive_link.mcp.notfound_guard import _UNKNOWN_TOOL_FALLBACK


async def _schemas(facade: Any) -> dict[str, set[str]]:
    return {t.name: set(t.parameters.get("properties", {})) for t in await facade.list_tools()}


def _source_refs() -> list[tuple[str, set[str]]]:
    out: list[tuple[str, set[str]]] = []
    for path in Path(strchive_link.__file__).parent.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "cmd":
                first = node.args[0] if node.args else None
                if isinstance(first, ast.Constant):
                    out.append((first.value, {k.arg for k in node.keywords if k.arg}))
                elif isinstance(first, ast.Name) and first.id == "_UNKNOWN_TOOL_FALLBACK":
                    out.append((_UNKNOWN_TOOL_FALLBACK, set()))
    return out


def _emitted(payload: Any) -> list[tuple[str, set[str]]]:
    steps = (payload.get("_meta") or {}).get("next_commands") or []
    return [(s["tool"], set(s.get("arguments") or {})) for s in steps]


def _assert_real(refs: list[tuple[str, set[str]]], schemas: dict[str, set[str]]) -> None:
    for tool, args in refs:
        assert tool in schemas, f"next_commands names unknown tool {tool!r}"
        assert args <= schemas[tool], f"{tool} has no argument(s) {args - schemas[tool]}"


async def test_source_templates_name_real_tools_and_arguments(facade: Any) -> None:
    refs = _source_refs()
    assert len(refs) >= 8  # the scan must actually find the templates
    _assert_real(refs, await _schemas(facade))


async def test_emitted_next_commands_name_real_tools_and_arguments(
    facade: Any, structured: Any
) -> None:
    from fastmcp import Client

    calls = [
        ("search_loci", {"query": "ataxia"}),
        ("search_loci", {"query": "zzzzqq"}),
        ("get_locus", {"locus": "HTT"}),
        ("get_locus", {"locus": "HTT", "response_mode": "standard"}),
        ("get_locus", {"locus": "ARX"}),
        ("get_locus", {"locus": "NOTAGENE"}),
        ("get_locus", {"locus": "Huntington disease"}),
        ("compare_repeat_length", {"locus": "HTT", "repeat_count": 40}),
        ("get_diagnostics", {}),
    ]
    refs: list[tuple[str, set[str]]] = []
    async with Client(facade) as client:
        for name, args in calls:
            result = await client.call_tool(name, args, raise_on_error=False)
            refs += _emitted(structured(result))
    assert refs
    _assert_real(refs, await _schemas(facade))
